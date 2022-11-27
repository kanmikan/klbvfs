#!/bin/env python3

#Script de pruebas y herramientas propias usadas para identificar trajes y personajes, entre otras pruebas que voy a estar haciendo

from klbvfs import *
import re
import json

###

#diccionario del id en la base de datos que hace referencia a cada personaje
names = {
1: "Honoka", 2: "Eli", 3: "Kotori", 4: "Umi", 5: "Rin", 6: "Maki", 7: "Nozomi", 8: "Hanayo", 9: "Nico",
101: "Chika", 102: "Riko", 103: "Kanan", 104: "Dia", 105: "You", 106: "Yoshiko", 107: "Hanamaru", 108: "Mary", 109: "Ruby", 
201: "Ayumu", 202: "Kasumi", 203: "Shizuku", 204: "Karin", 205: "Ai", 206: "Kanata", 207: "Setsuna", 208: "Emma", 209: "Rina", 210: "Shioriko", 211: "Mia", 212: "Lanzhu"
}

#precargar diccionario
try:
  json_dictionary = json.load(open('./m_dictionary.json'))
except FileNotFoundError:
  print("[Warning] Necesitas extraer el m_dictionary a un archivo json (m_dictionary.json)")
pass

###

def decrypt(pack_name, head, size, key1, key2, output):
  source = os.path.abspath(".")
  destination = os.path.join(output, "%s_%d" % (pack_name, head)) 
  
  #accede a la carpeta pkgx donde x es el primer digito del pack_name
  pkgpath = os.path.join(source, "pkg" + pack_name[:1], pack_name)
  
  key = [key1, key2, 0x3039] #el key es un array[3]
  try:
    pkg = codecs.open(pkgpath, mode='rb', encoding='klbvfs', errors=key) #abrir el archivo pkgx encriptado
    pkg.seek(head) #ir a la posicion que indica el head
    buffer = pkg.read(8)
    mimetype = magic.from_buffer(buffer, mime=True)
    extension = mimetypes.guess_extension(magic.from_buffer(buffer, mime=True))
    
    if mimetype == 'application/octet-stream':
      if buffer.startswith(b'UnityFS'):
        mimetype = "application/unityfs"
        extension = ".unity3d"
      elif buffer.startswith(b'\x89PNG'):
        mimetype = "image/png"
        extension = ".png"
      else:
        #print(buffer)
        pass
    
    key[0] = key1  # hack: reset rng state, codec has reference to this array
    key[1] = key2
    key[2] = 0x3039
    pkg.seek(head)
    print("[%s] decrypting to %s (%s)" % (destination, extension, mimetype))
    
    if os.path.exists(destination + extension):
      print("File already created - Skipping")
      pass
    else:
      with open(destination + extension, 'wb+') as dst:
        shutil.copyfileobj(pkg, dst, size)
    pkg.close()
    return destination + extension
    
  except FileNotFoundError:
    print("File not found!")
    pass

def getDictionaryValue(dictionary_key):
  filtered_json = json.dumps([element for element in json_dictionary if element['id'] == dictionary_key.split(".")[1]])  
  return re.sub('\W+',' ', json.loads(filtered_json)[0]["message"]).strip()


def unpack_character(character_id, output):
  source = os.path.abspath(".")
  destination = os.path.join(os.path.join(source, output), names[int(character_id)])
  try:
    os.makedirs(destination)
  except FileExistsError:
    pass
  
  masterdb = klb_sqlite(find_db('masterdata', source)).cursor()
  assetsdb = klb_sqlite(find_db('asset_a_en', source)).cursor()
  
  master_query = "select id, member_m_id, name, thumbnail_image_asset_path, model_asset_path from m_suit WHERE member_m_id == :character_id"
  for (id, member_m_id, name, thumbnail_image_asset_path, model_asset_path) in masterdb.execute(master_query, {'character_id': character_id}):
    item_full_name = getDictionaryValue(name)
    print(f"{id} - {item_full_name} - {thumbnail_image_asset_path} - {model_asset_path}")
    
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
  
  asset_query = f"SELECT asset_path, pack_name, head, size, key1, key2 FROM {table} WHERE pack_name == '{pack_name}'"
  for (asset_path, pack_name, head, size, key1, key2) in assetsdb.execute(asset_query):
    result = decrypt(pack_name, head, size, key1, key2, destination)
  return result


def decrypt_asset_on(table, asset_id, output):
  source = os.path.abspath(".")
  destination = os.path.join(source, output)
  try:
    os.makedirs(destination)
  except FileExistsError:
    pass
  assetsdb = klb_sqlite(find_db('asset_a_en', source)).cursor()
  asset_query = "SELECT asset_path, pack_name, head, size, key1, key2 FROM " + table + " WHERE asset_path == '" + asset_id.replace("'","''") + "'" #no tocar esto......
  print(asset_query)
  
  for (asset_path, pack_name, head, size, key1, key2) in assetsdb.execute(asset_query):
    result = decrypt(pack_name, head, size, key1, key2, destination)
  return result


def unpack_advscript(filepath, output):
  source = os.path.abspath(".")
  file = os.path.join(source, filepath)
  out = os.path.join(source, output)
  
  #LLAS LZ77 test (intento de implementacion parcial y limitada de esto: https://suyo.be/sifas/wiki/internals/advscript-format)
  with open(file, "rb") as f:
    f.seek(27) #saltear header
    data = bytearray(f.read())
    c = 0
    while (data.find(b'\x80', c+1) != -1):
      c = data.find(b'\x80', c+1)
      offset = int(data[c+1:c+2].hex(), 16) + 1
      length = int(data[c+2:c+3].hex(), 16) + 1
      if (c - offset + length) < c:
        value = data[c-offset: c-offset+length]
        data[c:c+1] = value
        data[c+length:c+length+2] = data[0:0] #mi hack para eliminar 2 bytes...
      else:
        value = data[c-offset: c-offset+length]
        c_pos = value.find(b'\x80')
        original_value = value[:c_pos]
        original_value_length = len(original_value)
        extra_length = length - original_value_length
        buff = original_value
        for i in range(extra_length-1):
          buff = buff + original_value
        data[c:c+1] = original_value + buff[:extra_length]
        data[c+length:c+length+2] = data[0:0]
    with open(out, 'wb+') as f:
      f.write(data)


#EXPERIMENTAL: test
def tests(args):
  source = os.path.abspath(".")
  destination = os.path.join(source, "unpacked_stages")
  try:
    os.makedirs(destination)
  except FileExistsError:
    pass

  masterdb = klb_sqlite(find_db('masterdata', args.source)).cursor()
  assetsdb = klb_sqlite(find_db('asset_a_en', args.source)).cursor()

  query = "SELECT DISTINCT m_live_mv.live_id, m_live_mv.live_stage_master_id, m_live_mv.live_3d_asset_master_id, m_live.name, m_live.jacket_asset_path, m_live_3d_asset.timeline, m_live_3d_asset.stage_effect_asset_path, m_live_3d_asset.live_prop_skeleton_asset_path, m_live_3d_asset.shader_variant_asset_path FROM m_live_mv INNER JOIN m_live ON m_live.live_id = m_live_mv.live_id INNER JOIN m_live_3d_asset ON m_live_3d_asset.id = m_live_mv.live_3d_asset_master_id"
  for (live_id, live_stage_master_id, live_3d_asset_master_id, name, jacket_asset_path, timeline, stage_effect_asset_path, live_prop_skeleton_asset_path, shader_variant_asset_path) in masterdb.execute(query):
    
    song_name = getDictionaryValue(name)
    print(f"{live_id} - {live_stage_master_id} - {live_3d_asset_master_id} - {song_name} - {jacket_asset_path} - {timeline} - {stage_effect_asset_path} - {live_prop_skeleton_asset_path} - {shader_variant_asset_path}")
    
    destination_path = os.path.join(destination, song_name)
    stage_destination_path = os.path.join(destination_path, "stage_models")
    try:
      os.makedirs(stage_destination_path)
    except FileExistsError:
      pass
    
    #extraer assets independientes (timeline, stage_effect_asset_path, etc)
    decrypt_asset_on("texture", jacket_asset_path, destination_path) #cover
    decrypt_asset_on("live_timeline", timeline, os.path.join(destination_path, "timeline"))
    decrypt_asset_on("stage_effect", stage_effect_asset_path, os.path.join(destination_path, "stage_effects"))
    #decrypt_asset_on("live_prop_skeleton", live_prop_skeleton_asset_path, os.path.join(destination_path, "live_prop_models")) #ejemplo: el megáfono de setsuna, NULL si no hay props.
    #decrypt_asset_on("shader", live_prop_skeleton_asset_path, os.path.join(destination_path, "live_shader")) #NULL si no hay custom shaders
    
    #extraer stages
    stage_asset_query = "SELECT DISTINCT m_asset_package_mapping.package_key, stage.pack_name, stage.head, stage.size, stage.key1, stage.key2 from stage INNER JOIN m_asset_package_mapping ON m_asset_package_mapping.pack_name = stage.pack_name WHERE m_asset_package_mapping.package_key == :package_key"
    for (package_key, pack_name, head, size, key1, key2) in assetsdb.execute(stage_asset_query, {'package_key': "live:" + str(live_3d_asset_master_id)}):
      print(f"{package_key} - {pack_name} - {head} - {size} - {key1} - {key2}")      
      decrypt(pack_name, head, size, key1, key2, stage_destination_path)



### TOOLS ACA ###
#UTILIDAD: desenpaqueta un advscript a texto plano
def advscript_unpack(args):
  advfile = decrypt_on("adv_script", args.pack_name, args.output)
  unpack_advscript(advfile, advfile + "_unpacked.txt")


#UTILIDAD: extrae un pack especifico en una tabla EJEMPLO: d member_model 108mqo
def decrypt_element(args):
  decrypt_on(args.table, args.pack_name, args.output)


#UTILIDAD: extrae todos los trajes de x personaje, junto con un thumbnail EJEMPLO: chu 101 modelos_extraidos
def chara_unpack(args):
  unpack_character(args.character_id, args.output)
  
#################

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Script de pruebas y herramientas propias')
  sub = parser.add_subparsers()
    
  test_help = 'codigo experimental'
  test = sub.add_parser('test', aliases=['tst'], help=test_help)
  test.add_argument('source', nargs='?', help=test_help, default='.')
  test.set_defaults(func=tests)
  
  chu_help = 'charaunpack character_id'
  chu = sub.add_parser('charaunpack', aliases=['chu'], help=chu_help)
  chu.add_argument('character_id', nargs='?', help=chu_help, default='1')
  chu.add_argument('output', nargs='?', help=chu_help, default='unpacked_character')
  chu.set_defaults(func=chara_unpack)
  
  dcr_help = 'decrypt table pack_name output'
  dcr = sub.add_parser('decrypt', aliases=['d'], help=dcr_help)
  dcr.add_argument('table', nargs='?', help=dcr_help, default='textures')
  dcr.add_argument('pack_name', nargs='?', help=dcr_help, default='none')
  dcr.add_argument('output', nargs='?', help=dcr_help, default='decrypted_output')
  dcr.set_defaults(func=decrypt_element)
  
  adv_help = 'advunpack pack_name output'
  adv = sub.add_parser('advunpack', aliases=['advu'], help=adv_help)
  adv.add_argument('pack_name', nargs='?', help=adv_help, default='none')
  adv.add_argument('output', nargs='?', help=adv_help, default='decrypted_output')
  adv.set_defaults(func=advscript_unpack)
  
  args = parser.parse_args(sys.argv[1:])
  if 'func' not in args:
    parser.parse_args(['-h'])
  args.func(args)
