"""Local room arrangement only: never implies a connection or changes a speaker."""
import json

ROOMS = ('Living room', 'Office', 'Kitchen', 'Bedroom')
# Ten non-overlapping sprite positions across four illustrated rooms.
SLOTS = ((0,.48,.46),(1,.81,.46),(2,.49,.78),(3,.86,.79),
         (0,.29,.47),(0,.38,.40),(1,.68,.47),(2,.32,.77),(3,.70,.78),(3,.80,.67))


class HouseLayout:
    def __init__(self, path):
        self.path = path
        self.rooms = list(ROOMS)
        self.positions = {}
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
            labels = saved.get('rooms')
            if isinstance(labels,list) and len(labels)==4 and all(isinstance(x,str) and 0<len(x.strip())<=24 for x in labels):
                self.rooms = [x.strip() for x in labels]
            positions = saved.get('positions',{})
            if isinstance(positions,dict):
                for key, slot in positions.items():
                    if isinstance(key,str) and key.isdecimal() and 0<int(key)<1<<48 and type(slot) is int and 0<=slot<10:
                        self.positions[int(key)] = slot
        except (OSError,ValueError,TypeError,AttributeError):
            pass

    def ensure(self, addresses):
        addresses = list(dict.fromkeys(addresses))
        if len(addresses)>10:
            raise ValueError('The house supports ten speakers: one main and nine guests.')
        taken=set()
        for address in addresses:
            slot=self.positions.get(address)
            if slot is None or slot in taken:
                slot=next(i for i in range(10) if i not in taken)
                self.positions[address]=slot
            taken.add(slot)

    def move(self,address,slot,active):
        self.ensure(active)
        if type(slot) is not int or not 0<=slot<10:
            raise ValueError('Choose a slot inside the house.')
        previous=self.positions[address]
        occupant=next((key for key in active if key!=address and self.positions.get(key)==slot),None)
        self.positions[address]=slot
        if occupant is not None:
            self.positions[occupant]=previous

    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'rooms':self.rooms,'positions':self.positions},indent=2),encoding='utf-8')
        temporary.replace(self.path)
