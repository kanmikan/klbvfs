#!/bin/env python3

#Script de pruebas y herramientas propias usadas para identificar trajes y personajes, entre otras pruebas que voy a estar haciendo

from klbvfs import *
import re

#diccionario del id en la base de datos que hace referencia a cada personaje
names = {
1: "Honoka", 2: "Eli", 3: "Kotori", 4: "Umi", 5: "Rin", 6: "Maki", 7: "Nozomi", 8: "Hanayo", 9: "Nico",
101: "Chika", 102: "Riko", 103: "Kanan", 104: "Dia", 105: "You", 106: "Yoshiko", 107: "Hanamaru", 108: "Mary", 109: "Ruby", 
201: "Ayumu", 202: "Kasumi", 203: "Shizuku", 204: "Karin", 205: "Ai", 206: "Kanata", 207: "Setsuna", 208: "Emma", 209: "Rina", 210: "Shioriko", 211: "Mia", 212: "Lanzhu"
}

def decrypt(pack_name, head, size, key1, key2, output):
  source = os.path.abspath(".")
  destination = os.path.join(output, "%s_%d" % (pack_name, head)) 
  
  #accede a la carpeta pkgx donde x es el primer digito del pack_name
  pkgpath = os.path.join(source, "pkg" + pack_name[:1], pack_name)
  
  key = [key1, key2, 0x3039] #el key es un array[3]
  try:
    pkg = codecs.open(pkgpath, mode='rb', encoding='klbvfs', errors=key) #abrir el archivo pkgx encriptado
    pkg.seek(head) #ir a la posicion que indica el head
    #buffer = pkg.read(1024)
    buffer = pkg.read(8)
    mimetype = magic.from_buffer(buffer, mime=True)
    extension = mimetypes.guess_extension(magic.from_buffer(buffer, mime=True))
    
    if mimetype == 'application/octet-stream':
      print("buffer: %s" % (buffer))
      if buffer.startswith(b'UnityFS'):
        mimetype = "application/unityfs"
        extension = ".unity3d"
      else:
        print(buffer)
        pass
    
    key[0] = key1  # hack: reset rng state, codec has reference to this array
    key[1] = key2
    key[2] = 0x3039
    pkg.seek(head)
    print("[%s] decrypting to %s (%s)" % (destination, extension, mimetype))
    with open(destination + extension, 'wb+') as dst:
      shutil.copyfileobj(pkg, dst, size)
    pkg.close()
    return output
    
  except FileNotFoundError:
    print("File not found!")
    pass


#UTILIDAD: ordenar carpetas (despues de la extraccion usando ./klbvfs.py dump --types=member_model) añadiendo el nombre del personaje al que pertenecen al principio.
def orderSuits(args):
  masterdb = klb_sqlite(find_db('masterdata', args.directory)).cursor()
  dirlist = os.listdir("./member_model/suit/")

  for cdir in dirlist:
    #SQL query a la base de datos pidiendo la celda con la info del id del traje (el nombre de la carpeta)
    master_query = "select id, member_m_id from m_suit WHERE id == " + cdir
    #para cada traje encontrado (debería ser solo uno pero bueh) renombrar la carpeta añadiendo al principio el nombre del personaje.
    for (id, member_m_id) in masterdb.execute(master_query):
      try:
        print(names[member_m_id])
        os.rename("./member_model/suit/" + cdir + "/", "./member_model/suit/" + names[member_m_id] + "_" + cdir + "/")
      except Exception:
        #ignorar errores cuando no existe la carpeta, o alguna otra tonteria.
        pass

def unpack_character(character_id, output):
  import json
  source = os.path.abspath(".")
  destination = os.path.join(os.path.join(source, output), names[int(character_id)])
  try:
    os.makedirs(destination)
  except FileExistsError:
    pass
  
  masterdb = klb_sqlite(find_db('masterdata', source)).cursor()
  assetsdb = klb_sqlite(find_db('asset_a_en', source)).cursor()
  try:
    json_dictionary = json.load(open('./m_dictionary.json')) #entonces uso un json extraido usando la gui de SQLite
  except FileNotFoundError:
    print("Necesitas extraer el m_dictionary a un archivo json (m_dictionary.json)")
    pass
  
  for (id, member_m_id, name, thumbnail_image_asset_path, model_asset_path) in masterdb.execute("select id, member_m_id, name, thumbnail_image_asset_path, model_asset_path from m_suit WHERE member_m_id == :character_id", {'character_id': character_id}):
    filtered_json = json.dumps([element for element in json_dictionary if element['id'] == name.split(".")[1]])  
    item_full_name = re.sub('\W+',' ', json.loads(filtered_json)[0]["message"]).strip()
    
    print("%s - %s - %s - %s" % (id, item_full_name, thumbnail_image_asset_path, model_asset_path))
    
    texture_asset_query = "select asset_path, pack_name, head, size, key1, key2 from texture WHERE asset_path == :path"
    for (asset_path, pack_name, head, size, key1, key2) in assetsdb.execute(texture_asset_query, {'path': thumbnail_image_asset_path}):
      destination_path = os.path.join(destination, item_full_name)
      try:
        os.makedirs(destination_path)
      except FileExistsError:
        pass
      decrypt(pack_name, head, size, key1, key2, destination_path)
    
    model_asset_query = "select DISTINCT m_asset_package_mapping.package_key, member_model.pack_name, member_model.head, member_model.size, member_model.key1, member_model.key2 from member_model INNER JOIN m_asset_package_mapping ON m_asset_package_mapping.pack_name = member_model.pack_name where m_asset_package_mapping.package_key == :package_key"
    destination_path = os.path.join(destination, item_full_name + "/model")
    try:
      os.makedirs(destination_path)
    except FileExistsError:
      pass
    
    with mp.Pool() as pool:
      results = []
      try:
        for (package_key, pack_name, head, size, key1, key2) in assetsdb.execute(model_asset_query, {'package_key': "suit:" + str(id)}):
          print("%s - %s - %s - %s - %s - %s" % (package_key, pack_name, head, size, key1, key2))
          results.append(pool.apply_async(decrypt, (pack_name, head, size, key1, key2, destination_path)))  
      except Exception:
        print("Error en el pool desencriptando los modelos.")
        pass
      for result in results:
        print("[%s] done" % result.get())


def decrypt_on(table, pack_name, output):
  source = os.path.abspath(".")
  destination = os.path.join(os.path.join(source, output + "/" + table), pack_name)
  try:
    os.makedirs(destination)
  except FileExistsError:
    pass

  assetsdb = klb_sqlite(find_db('asset_a_en', source)).cursor()
  asset_query = "select asset_path, pack_name, head, size, key1, key2 from " + table + " WHERE pack_name == '" + pack_name + "'"

  for (asset_path, pack_name, head, size, key1, key2) in assetsdb.execute(asset_query):
    decrypt(pack_name, head, size, key1, key2, destination)


#EXPERIMENTAL: descomprimir el texto de un adv_script a UTF-8... probablemente...
def tests(args):
  source = os.path.abspath(".")
  #file = os.path.join(source, "decrypted_output/adv_script/4pkzzh/4pkzzh_0.bin")
  #out = os.path.join(source, "decrypted_output/adv_script/4pkzzh/4pkzzh_0.txt")
  file = os.path.join(source, args.filepath)
  out = os.path.join(source, args.filepath + ".txt")
  
  #LLAS LZ77 test (intento de implementacion parcial y limitada de esto: https://suyo.be/sifas/wiki/internals/advscript-format)
  with open(file, "rb+") as f:
    f.seek(27) #saltear header
    data = bytearray(f.read())
    c = 0
    while (data.find(b'\x80', c+1) != -1):
      c = data.find(b'\x80', c+1)
      #print(c)
      offset = int(data[c+1:c+2].hex(), 16) + 1
      lenght = int(data[c+2:c+3].hex(), 16) + 1
    
      #print(data[c:c+1])
      #print(offset)
      #print(lenght)
      if (c - offset + lenght) < c:
        value = data[c-offset: c-offset+lenght]
        print(value)
        data[c:c+1] = value
        data[c+lenght:c+lenght+2] = data[0:0] #mi hack para eliminar 2 bytes...
      else:
        #print("lenght es mayor al offset")
        value = data[c-offset: c-offset+lenght]
        c_pos = value.find(b'\x80')
        original_value = value[:c_pos]
        original_value_lenght = len(original_value)
        extra_lenght = lenght - original_value_lenght
        
        buff = original_value
        for i in range(extra_lenght-1):
          buff = buff + original_value
        
        result_value = original_value + buff[:extra_lenght]
        
        data[c:c+1] = result_value
        data[c+lenght:c+lenght+2] = data[0:0]
        
 
    with open(out, 'wb+') as f:
      f.write(data)
    


### TOOLS ACA ###

#UTILIDAD: extrae un pack especifico en una tabla EJEMPLO: d member_model 108mqo
def decrypt_element(args):
  decrypt_on(args.table, args.pack_name, args.output)

#UTILIDAD: extrae todos los trajes de x personaje, junto con un thumbnail EJEMPLO: chu 101 modelos_extraidos
def charaunpack(args):
  unpack_character(args.character_id, args.output)

#################

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Script de pruebas y herramientas propias')
  sub = parser.add_subparsers()
  
  osuits_help = 'ordena las carpetas de member_model/suit en base al nombre del personaje al que pertenece el traje'
  osuits = sub.add_parser('orderSuits', aliases=['osuits'], help=osuits_help)
  osuits.add_argument('directory', nargs='?', help=osuits_help, default='.')
  osuits.set_defaults(func=orderSuits)
    
  test_help = 'codigo experimental'
  test = sub.add_parser('test', aliases=['tst'], help=test_help)
  test.add_argument('filepath', nargs='?', help=test_help, default='.')
  test.set_defaults(func=tests)
  
  chu_help = 'charaunpack character_id'
  chu = sub.add_parser('charaunpack', aliases=['chu'], help=chu_help)
  chu.add_argument('character_id', nargs='?', help=chu_help, default='1')
  chu.add_argument('output', nargs='?', help=chu_help, default='unpacked_character')
  chu.set_defaults(func=charaunpack)
  
  dcr_help = 'decrypt table pack_name'
  dcr = sub.add_parser('decrypt', aliases=['d'], help=dcr_help)
  dcr.add_argument('table', nargs='?', help=dcr_help, default='textures')
  dcr.add_argument('pack_name', nargs='?', help=dcr_help, default='none')
  dcr.add_argument('output', nargs='?', help=dcr_help, default='decrypted_output')
  dcr.set_defaults(func=decrypt_element)
  
  args = parser.parse_args(sys.argv[1:])
  if 'func' not in args:
    parser.parse_args(['-h'])
  args.func(args)
