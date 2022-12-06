#!/bin/env python3
import os
import re
import base64
import urllib.parse
import subprocess
import zlib
from functools import partial

from klbvfs import *

##GLOBALES##
root = os.path.abspath(".")
dump_folder = os.path.join(root, "dump")
output_folder = os.path.join(root, "extracted")
app_package = "com.klab.lovelive.allstars.global" #TODO: detectar las demás versiones


##UTILS##
def read_SQKey():
  shared_prefs_path = os.path.join(os.path.join(dump_folder, "shared_prefs"), app_package + '.v2.playerprefs.xml')
  xml_file = open(shared_prefs_path, 'r').read()
  sqm = re.search("(SQ).+", xml_file)
  sq = urllib.parse.unquote(xml_file[sqm.start()+4:sqm.end()-9])
  sq = base64.b64decode(sq)
  return sq
  
  
def sqlite_key(dbfile):
  sqkey = read_SQKey()
  basename = os.path.basename(dbfile)
  sha1 = hmac_sha1(key=sqkey, s=basename.encode('utf-8'))
  return list(struct.unpack('>III', sha1[:12]))


def decrypt_db(source):
  dstpath = '_'.join(source.split('_')[:-1])
  print(os.path.basename(dstpath))
  
  src = codecs.open(source, mode='rb', encoding='klbvfs', errors=sqlite_key(source))
  dst = open(dstpath, 'wb+')
  
  print('decrypting databases %s -> %s' % (source, dstpath))
  shutil.copyfileobj(src, dst)
  src.close()
  dst.close()
  return dstpath


#https://heapspray.io/decompressing-android-backups-python.html
def ab_unpack(source, destination):
  print("Extraccion del ab en progreso...")
  abfile = open(source, "rb")
  output = open(destination, "wb")
  abfile.seek(24)
  obj = zlib.decompressobj(zlib.MAX_WBITS) 
  for chunk in iter(partial(abfile.read, 1024), ""):
    if chunk == b'':
      output.flush()
      output.close()
      break;
    out_chunk = obj.decompress(chunk)
    output.write(out_chunk)
  print("Extraccion completada.")


##ACCIONES##
#extraer datos del juego desde el dispositivo, y mover los archivos a su respectiva carpeta
def dump():
  raw_folder = os.path.join(dump_folder, "raw")
  #solo para ver si esta conectado el dispositivo.
  subprocess.run(["adb", "devices"])
  
  #hacer dump de todos los datos
  #subprocess.run(["adb", "pull", "/sdcard/Android/data/"+app_package, os.path.join(raw_folder, app_package)])
  
  #hacer backup de la app para extraer el shared_prefs (por alguna razón, el dump no extrae todos los archivos, por eso es necesario tambien hacer adb pull)
  subprocess.run(["adb", "backup", "-shared", app_package, "-f", os.path.join(raw_folder, "dump.ab")])
  
  #convertir el ab a tar
  ab_unpack(os.path.join(raw_folder, "dump.ab"), os.path.join(raw_folder, "dump.tar"))
  
  #extraer el shared preference desde el tar.
  os.chdir(raw_folder)
  subprocess.run(["tar", "-xvf", os.path.join(raw_folder, "dump.tar"), "apps/"+app_package+"/sp/"+app_package+".v2.playerprefs.xml"])
  os.chdir(root)


#preparar entorno la primera vez
def init():
  #mover shared_prefs DE raw/apps/{app_package}/sp/*.xml A dump/shared_prefs
  #mover *.db DE raw/{app_package}/files/files/ A dump/databases
  #mover packs DE raw/{app_package}/files/files/ A dump/packs
  
  #desencriptar bases de datos
  print("Desencriptando las bases de datos, esto puede tardar.")
  db_folder = os.path.join(dump_folder, "db")
  for dbfile in os.listdir(db_folder):
    decrypt_db(os.path.join(db_folder, dbfile))
  print("Bases de datos desencriptadas.")


#actualizar packs y bases de datos
def update():
  print("TODO")
  #borrar el contenido de la carpeta raw
  #ejecutar dump()
  #desencriptar base de datos y reemplazar los viejos
  #mover packs del raw a dump/packs pero sin reemplazar los ya existentes.


#acciones para desempaquetar
def unpack():
  print("TODO")
  #klbvfs y tools.py pero adaptado al esquema de directorios de lab.py


##TESTS##
dump()
#init()

