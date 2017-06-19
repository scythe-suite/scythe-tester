from base64 import decodestring
import io
from logging import basicConfig, getLogger, DEBUG, INFO
from os import environ, chmod, unlink
from shutil import rmtree
from tarfile import TarFile
from tempfile import mkdtemp

from redis import StrictRedis

LOG_LEVEL = INFO
basicConfig(format = '%(asctime)s %(levelname)s: %(message)s', datefmt = '%Y-%m-%d %H:%M:%S', level = LOG_LEVEL)
LOGGER = getLogger(__name__)

VERSION = '0.1.1'

redis = StrictRedis.from_url(environ.get('SCYTHE_REDIS_URL', 'redis://localhost'))

def rmrotree(path):
    def _oe(f, p, e):
        if p == path: return
        pp = dirname(p)
        chmod(pp, 0700)
        chmod(p, 0700)
        unlink(p)
    rmtree(path, onerror = _oe)

def tar2tmpdir(source, decode = False):
    if decode:
        fo = io.BytesIO(decodestring(source))
    else:
        fo = io.open(source, 'rb')
    temp_dir = mkdtemp(prefix = 'scythe-', dir = '/tmp' )
    with TarFile.open(mode = 'r', fileobj = fo) as tf:
        try:
            tf.extractall(temp_dir)
        except IOError:
            rmrotree(temp_dir)
            return None
    return temp_dir
