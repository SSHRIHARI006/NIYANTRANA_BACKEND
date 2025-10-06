import pulp
from typing import List
from Train import Train
SLOTS = [f"IBL-{i:02d}_S{j}" for i in range(1,4) for j in [1,2]] + [f"SBL-{i:02d}_S{j}" for i in range(1,12+1) for j in [1,2]]

# mere comments change mat karna mujhe badme dikkat ati hai, pichli bar comment change kardiye the tumlog 😤

# ok dekh firse MILP hi use kar raha hu pehele greedy bana raha tha toh usme dikkat arahi thi
# to phele apan ek value calculate kareneg for every trains and slot x_t_s 
# ye x hoga wo situation jisme hum t train ko s slot pe assign kar rahe hai
# ab is operation ka cost calculate karenge c_t_s 
# fir in dono ko multi ply karke for every combination of t and s inka sum nikalenge ye hoga objective function
# ab is objective function ko mimimze kar denge fir ho jayega

#boundaries and calculations wagera pg-13 pe hai - ignore everybody mere liye hai

def slot_cost(train, slot):
    '''
        agar IBL hua toh :
            maintainece wale tranins ko 0 cost denge 
            warna bohot bara cost dedenge 
            - is se IBL me humesha maintanence wale hi ayenge
        
        agr SBL hua toh :
            Slot 1 :
                service ko 0 cost do
                standby bhi chalega toh mid level ka cost
                maintainancece walo ko bada sa cost dedo taki select na ho
            Slot 2:
                isme standby wale ko 0 dedo
                maintaince ko bhi kam do cost
                service ko zada dedo
                
    '''

    if slot.startswith("IBL"):
        if train.status == "MAINTENANCE": return 0
        else: return 100
    elif slot.endswith("S1"):
        if train.status == "SERVICE": return 0
        elif train.status == "STANDBY": return 2
        elif train.status == "MAINTENANCE": return 10
    elif slot.endswith("S2"):
        if train.status == "SERVICE": return 10
        elif train.status == "STANDBY": return 0
        elif train.status == "MAINTENANCE": return 2
    return 1000

def assign_slots(all_trains :List[Train] ):
    TRAIN_IDS = [t.train_id for t in all_trains]
    y = pulp.LpVariable.dicts("assign", [(t, s) for t in TRAIN_IDS for s in SLOTS], cat="Binary")

    
    cost_terms = []
    for train in all_trains:
        for slot in SLOTS:
            cost = slot_cost(train, slot)
            cost_terms.append(cost * y[(train.train_id, slot)])

    model = pulp.LpProblem("TrainToSlotAssignment", pulp.LpMinimize)
    model += pulp.lpSum(cost_terms)

    for t in TRAIN_IDS:
        model += pulp.lpSum([y[(t, s)] for s in SLOTS]) == 1  # har train ko ek hi slot mile
    for s in SLOTS:
        model += pulp.lpSum([y[(t, s)] for t in TRAIN_IDS]) <= 1  # ek slot me ek hi train

    model.solve(pulp.PULP_CBC_CMD(msg=1))
    return {s: t for t in TRAIN_IDS for s in SLOTS if pulp.value(y[(t, s)]) > 0.5}


