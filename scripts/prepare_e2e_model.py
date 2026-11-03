import threading
from pathlib import Path
from subtitleflow.models import ModelManager
manager=ModelManager(Path('.work/models'))
for key in ('base','small'):
    if not manager.ready(key,threading.Event()):
        manager.install(key,threading.Event(),lambda a,b:None)
