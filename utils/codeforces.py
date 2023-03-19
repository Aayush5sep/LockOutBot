import json
import random
import math

from utils import cf_api
from data import dbconn

db = dbconn.DbConn()
cf = cf_api.CodeforcesAPI()

authors = None




async def filter_problems(all_problems, user_problems):
    unsolved = []
    names = [x.name for x in user_problems]
    names.sort()

    for problem in all_problems:

        found = False
        l, r = 0, len(names) - 1
        while l <= r:
            mid = int((l+r)/2)
            if names[mid] > problem.name:
                r = mid - 1
            elif names[mid] < problem.name:
                l = mid + 1
            else:
                found = True
                break

        if not found:
            unsolved.append(problem)

    return unsolved


async def find_problems(handles, ratings):
    all_problems = db.get_problems()
    user_problems = []
    for handle in handles:
        resp = await cf.get_user_problems(handle)
        if not resp[0]:
            return resp
        user_problems.extend(resp[1])

    user_problems = list(set(user_problems))

    unsolved_problems = await filter_problems(all_problems, user_problems)

    selected = []
    for x in ratings:
        problem = None
        options = [p for p in unsolved_problems if p.rating == x and p not in selected]
        weights = [int(p.id * math.sqrt(p.id)) for p in options]
        if options:
            problem = random.choices(options, weights, k=1)[0]
        if not problem:
            return [False, f"Not enough problems with rating {x} left!"]
        selected.append(problem)

    return [True, selected]


async def get_solve_time(sub, id, index):
    best = 1e18
    for x in sub:
        if x.id == int(id) and x.index == index:
            if x.verdict == 'OK':
                best = min(best, x.sub_time)
            if x.verdict is None or x.verdict == 'TESTING':
                return -1
    return best
