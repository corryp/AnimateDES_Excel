import random as rnd
import simpy

class Anides:
    def __init__(self, ac_script_fname, ad_start, ad_end):
        self.f_script = open(ac_script_fname,'w')
        self.f_script.write("time,target,value\n")
        self.d_start = ad_start
        self.d_end = ad_end
        self.b_closed = False

    def log_event(self, ad_t, ac_target, a_label):
        if self.b_closed:
            return
        if self.d_start <= ad_t and ad_t <= self.d_end:
            self.f_script.write(str(ad_t) + ',' + ac_target + ',' + str(a_label) + '\n')
        elif (ad_t > self.d_end):
            self.f_script.close()
            self.b_closed = True

    def move_entity(self, ad_t, ac_label, ac_path, ad_mvt):
        if self.b_closed:
            return
        if self.d_start <= ad_t and ad_t <= self.d_end:
            self.f_script.write(str(ad_t) + ',move,' + ac_label + ',' + ac_path + ',' + str(ad_mvt) + '\n')
        elif (ad_t > self.d_end):
            self.f_script.close()
            self.b_closed = True       
        
class AniPMC:
    def __init__(self, ad_start, ad_end, ai_n_shovel):
        self.ani = Anides("script.csv", ad_start, ad_end)
        self.i_shvl_q = [0 for i in range(ai_n_shovel)]
        self.i_shvl_trav = [0 for i in range(ai_n_shovel)]
        self.i_crush_q = 0
        self.i_crush_trav = 0

        self.ani.log_event(0, 'crush_busy', 0)
        self.ani.log_event(0, 'crush_trv', 0)
        self.ani.log_event(0, 'crush_q', 0)
        for i in range(ai_n_shovel):
            self.ani.log_event(0, 'shvl_busy' + str(i), 0)
            self.ani.log_event(0, 'shvl_trv' + str(i), 0)
            self.ani.log_event(0, 'shvl_q' + str(i), 0)

    def log_shvl_trav(self, ad_t, ai_shvl_id, ac_truck_nm, ad_mvt):
        self.i_shvl_trav[ai_shvl_id] += 1
        self.ani.log_event(ad_t, 'shvl_trv' + str(ai_shvl_id), self.i_shvl_trav[ai_shvl_id])
        self.ani.move_entity(ad_t, ac_truck_nm, "CtoS" + str(ai_shvl_id), ad_mvt)
        self.ani.log_event(ad_t, 'crush_busy', 0)

    def log_shvl_enq(self, ad_t, ai_shvl_id):
        if self.i_shvl_trav[ai_shvl_id] > 0:
            self.i_shvl_trav[ai_shvl_id] -= 1
        self.i_shvl_q[ai_shvl_id] += 1
        self.ani.log_event(ad_t, 'shvl_trv' + str(ai_shvl_id), self.i_shvl_trav[ai_shvl_id])
        self.ani.log_event(ad_t, 'shvl_q' + str(ai_shvl_id), self.i_shvl_q[ai_shvl_id])

    def log_shvl_start(self, ad_t, ai_shvl_id, ac_truck_nm):
        self.i_shvl_q[ai_shvl_id] -= 1
        self.ani.log_event(ad_t, 'shvl_q' + str(ai_shvl_id), self.i_shvl_q[ai_shvl_id])
        self.ani.log_event(ad_t, 'shvl_busy' + str(ai_shvl_id), ac_truck_nm)
        
    def log_crush_trav (self, ad_t, ai_shvl_id, ac_truck_nm, ad_mvt):
        self.i_crush_trav += 1
        self.ani.log_event(ad_t, 'crush_trv', self.i_crush_trav)
        self.ani.move_entity(ad_t, ac_truck_nm, 'S' + str(ai_shvl_id) + "toC", ad_mvt)
        self.ani.log_event(ad_t, 'shvl_busy' + str(ai_shvl_id), 0)

    def log_crush_enq (self, ad_t):
        self.i_crush_trav -= 1
        self.i_crush_q += 1
        self.ani.log_event(ad_t, 'crush_trv', self.i_crush_trav)
        self.ani.log_event(ad_t, 'crush_q', self.i_crush_q)

    def log_crush_start (self, ad_t, truck_nm):
        self.i_crush_q -= 1
        self.ani.log_event(ad_t, 'crush_q', self.i_crush_q)
        self.ani.log_event(ad_t, 'crush_busy', truck_nm)
        


class Truck:
    def __init__(self, env, name,
                 shovel_num, shovel, crusher,
                 load_a, load_b, travel_a, travel_b, unload_a, unload_b,
                 capacity, priority, ani):
        self.env = env
        self.name = name
        self.shovel_num = shovel_num
        self.shovel = shovel
        self.crusher = crusher
        self.load_a = load_a
        self.load_b = load_b
        self.travel_a = travel_a
        self.travel_b = travel_b
        self.unload_a = unload_a
        self.unload_b = unload_b
        self.capacity = capacity
        self.priority = priority
        self.ani = ani

        self.tons_crushed = 0
        
        self.process = env.process(self.truck_process())

    def truck_process(self):
        cycle = 0
        while True:
            cycle += 1
            self.print_event(cycle,'ready to load')
 
            #request shovel and wait until front of queue and shovel ready
            self.ani.log_shvl_enq(self.env.now, self.shovel_num-1)
            req = self.shovel.request()
            yield req

            #delay for loading
            self.print_event(cycle,'start loading')
            self.ani.log_shvl_start(self.env.now, self.shovel_num-1, self.name);
            yield self.env.timeout(self.load_a + rnd.expovariate(1.0 / self.load_b))
            self.print_event(cycle,'end loading')
            self.shovel.release(req)

            #delay for travel to crusher
            dtrvt = self.travel_a + rnd.expovariate(1.0 / self.travel_b)
            self.ani.log_crush_trav(self.env.now, self.shovel_num-1, self.name, dtrvt);
            yield self.env.timeout(dtrvt)            
            self.print_event(cycle,'ready to unload')
            
            #request crusher and wait until front of queue and crusher ready
            self.ani.log_crush_enq(self.env.now);
            req = self.crusher.request(self.priority)
            yield req

            #delay for unloading
            self.print_event(cycle,'start unloading')
            self.ani.log_crush_start(self.env.now, self.name);
            yield self.env.timeout(self.unload_a + rnd.expovariate(1.0 / self.unload_b))
            self.print_event(cycle,'end unloading')
            self.crusher.release(req)

            #update total tons crushed
            self.tons_crushed += self.capacity

            #delay for travel to shovel
            dtrvt = self.travel_a + rnd.expovariate(1.0 / self.travel_b)
            self.ani.log_shvl_trav(self.env.now, self.shovel_num-1, self.name, dtrvt)
            yield self.env.timeout(dtrvt)

    def print_event(self, cycle_num, event):
        if PRINT_ALL:
            print(str(round(self.env.now,2)) +','+ str(self.shovel_num) +','+ self.name +','+ str(cycle_num) +','+ event)

#settings
SIM_END = 1000
PRIORITY_50t = 0   #0=>higher priority, 1=>equal priority to 20t trucks
PRINT_ALL = False      #set to False to surpress verbose printing
ANIM_START = 0
ANIM_END = 100

if PRINT_ALL:
    print ("time,shovel,truck,cycle,event")  #headings for output log

#initialise simulation objects
env = simpy.Environment()
g_ani = AniPMC(ANIM_START, ANIM_END, 3)   #3 shovels

shovels = []     #store references to the 3 shovel Resource objects in a list
shovels.append(simpy.Resource(env, 1))
shovels.append(simpy.Resource(env, 1))
shovels.append(simpy.Resource(env, 1))

crusher = simpy.PriorityResource(env,1)

#convenient to specify travel times using lists of tuples, since travel time varies by shovel
travel20 = [(2.5,0.5),(0.75,0.5),(1.75,0.5)]
travel50 = [(2.9,0.5),(0.9,0.5),(1.9,0.5)]

trucks = []  #store references to all the Truck objects in a list
for i in range(len(shovels)):  #for each shovel in the list, create 3 trucks assigned to that shovel
    name = "20t" + str(i+1) +"1"
    trucks.append(Truck(env, name, i+1, shovels[i], crusher, 3.5, 1.5, travel20[i][0], travel20[i][1], 1.5, 0.5, 20, 1, g_ani))
    name = "20t" + str(i+1) +"2"
    trucks.append(Truck(env, name, i+1, shovels[i], crusher, 3.5, 1.5, travel20[i][0], travel20[i][1], 1.5, 0.5, 20, 1, g_ani))
    name = "50t" + str(i+1) +"3"    
    trucks.append(Truck(env, name, i+1, shovels[i], crusher, 8.0, 2.0, travel50[i][0], travel50[i][1], 2.8, 1.2, 50, PRIORITY_50t, g_ani))

#run simulation
env.run(until = SIM_END)

#show simulation results
total_tons = sum (tr.tons_crushed for tr in trucks)

print("TOTAL TONS =", total_tons)
print("TONS/HR =", total_tons / (SIM_END/60.0))


