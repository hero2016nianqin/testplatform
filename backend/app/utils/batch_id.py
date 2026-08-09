import hashlib
import os
from datetime import datetime


def generate_batch_id() -> str:
    now = datetime.now()
    rand_hex = hashlib.sha256(os.urandom(8)).hexdigest()[:8]
    return now.strftime("%Y%m%d%H%M%S") + "-" + rand_hex
