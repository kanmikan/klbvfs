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
    buffer = pkg.read(1024)
    mimetype = magic.from_buffer(buffer, mime=True)
    extension = mimetypes.guess_extension(magic.from_buffer(buffer, mime=True))
    
    if mimetype == 'application/octet-stream':
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


#EXPERIMENTAL: Ordenar elementos al momento de desencriptar, en base al personaje y el nombre del traje (mas o menos)
def tests(args):
  import json
  masterdb = klb_sqlite(find_db('masterdata', args.directory)).cursor()
  assetsdb = klb_sqlite(find_db('asset_a_en', args.directory)).cursor()
  #dictionary = klb_sqlite(find_db('dictionary_en_k', args.directory)).cursor() #así debería ser pero, por alguna razon dice que está encriptado y no se ejecuta
  
  try:
    json_dictionary = json.load(open('./m_dictionary.json')) #entonces uso un json extraido usando la gui de SQLite
  except FileNotFoundError:
    print("Necesitas extraer el m_dictionary a un archivo json (m_dictionary.json)")
    pass

  #se lee la lista de suits (texturas de los trajes 3d) de la masterdata
  for (id, member_m_id, name, thumbnail_image_asset_path, model_asset_path) in masterdb.execute("select id, member_m_id, name, thumbnail_image_asset_path, model_asset_path from m_suit"):
    print("%s - %s - %s - %s" % (id, member_m_id, thumbnail_image_asset_path, model_asset_path))
    
    filtered_json = json.dumps([element for element in json_dictionary if element['id'] == name.split(".")[1]])  
    item_full_name = json.loads(filtered_json)[0]["message"];
    spl = item_full_name.split(" ");
      
    #item_character = spl[len(spl)-2] + " " + spl[len(spl)-1];
    item_character = names[member_m_id]; #no siempre ponen el nombre del personaje al final.
    item_name = re.sub('\W+',' ', " ".join(spl[:-2 or None]))
    print("%s, %s" % (item_name, item_character))
    
    
    #TODO: unir las dos querys en una, pero ahora me da igual.
    #extraer Icono del suit
    texture_asset_query = "select asset_path, pack_name, head, size, key1, key2 from texture WHERE asset_path == :path"
    for (asset_path, pack_name, head, size, key1, key2) in assetsdb.execute(texture_asset_query, {'path': thumbnail_image_asset_path}):
      #creo la carpeta donde colocar la info del traje, ordenado usando: /outfit_info/nombre_personaje/nombre_del_traje/
      destination_path = "./outfit_info/%s/%s" % (item_character, item_name.strip())
      try:
        os.makedirs(destination_path)
      except FileExistsError:
        pass
      decrypt(pack_name, head, size, key1, key2, destination_path)
    
    #extraer modelo
    model_asset_query = "select asset_path, pack_name, head, size, key1, key2 from member_model WHERE asset_path == :path"
    for (asset_path, pack_name, head, size, key1, key2) in assetsdb.execute(model_asset_query, {'path': model_asset_path}):
      #creo la carpeta donde colocar la info del traje, ordenado usando: /outfit_info/nombre_personaje/nombre_del_traje/model/
      destination_path = "./outfit_info/%s/%s/model" % (item_character, item_name.strip())
      try:
        os.makedirs(destination_path)
      except FileExistsError:
        pass
      decrypt(pack_name, head, size, key1, key2, destination_path)

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
  test.add_argument('directory', nargs='?', help=test_help, default='.')
  test.set_defaults(func=tests)
  
  chu_help = 'charaunpack character_id'
  chu = sub.add_parser('charaunpack', aliases=['chu'], help=chu_help)
  chu.add_argument('character_id', nargs='?', help=chu_help, default='1')
  chu.add_argument('output', nargs='?', help=chu_help, default='unpacked_character')
  chu.set_defaults(func=charaunpack)
  
  dcr_help = 'decrypt_on table pack_name'
  dcr = sub.add_parser('decrypt', aliases=['d'], help=dcr_help)
  dcr.add_argument('table', nargs='?', help=dcr_help, default='textures')
  dcr.add_argument('pack_name', nargs='?', help=dcr_help, default='none')
  dcr.add_argument('output', nargs='?', help=dcr_help, default='decrypted_output')
  dcr.set_defaults(func=decrypt_element)
  
  args = parser.parse_args(sys.argv[1:])
  if 'func' not in args:
    parser.parse_args(['-h'])
  args.func(args)
