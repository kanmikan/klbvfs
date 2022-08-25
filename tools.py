#!/bin/env python3

#Script de pruebas y herramientas propias usadas para identificar trajes y personajes, entre otras pruebas que voy a estar haciendo

from klbvfs import *

#diccionario del id en la base de datos que hace referencia a cada personaje
names = {
1: "Honoka", 2: "Eli", 3: "Kotori", 4: "Umi", 5: "Rin", 6: "Maki", 7: "Nozomi", 8: "Hanayo", 9: "Nico",
101: "Chika", 102: "Riko", 103: "Kanan", 104: "Dia", 105: "You", 106: "Yoshiko", 107: "Hanamaru", 108: "Mary", 109: "Ruby", 
201: "Ayumu", 202: "Kasumi", 203: "Shizuku", 204: "Karin", 205: "Ai", 206: "Kanata", 207: "Setsuna", 208: "Emma", 209: "Rina", 210: "Shioriko", 211: "Mia", 212: "Lanzhu"
}

#ordenar carpetas añadiendo el nombre del personaje al que pertenecen al principio.
def orderSuits(args):
  #cursor en la base de datos "masterdata"
  masterdb = klb_sqlite(find_db('masterdata', args.directory)).cursor()
  
  #listar el contenido de la carpeta member_model/suit, creada por el comando: ./klbvfs.py dump --types=member_model
  dirlist = os.listdir("./member_model/suit/")
  for cdir in dirlist:
    #SQL query a la base de datos pidiendo la celda con la info del id del traje (el nombre de la carpeta)
    master_query = "select id, member_m_id from m_suit WHERE id == " + cdir
    #para cada traje encontrado (debería ser solo uno pero bueh) renombrar la carpeta añadiendo al principio el nombre del personaje.
    for (id, member_m_id) in masterdb.execute(master_query):
      try:
        print(names[member_m_id])
        #os.rename("./member_model/suit/" + cdir + "/", "./member_model/suit/" + names[member_m_id] + "_" + cdir + "/")
      except Exception:
        #ignorar errores cuando no existe la carpeta, o alguna otra tonteria.
        pass



#renombrar las carpetas de /member_model a los nombres de la carta
def test(args):
  import re
  
  #cursor de la base de datos masterdata
  masterdb = klb_sqlite(find_db('masterdata', args.directory)).cursor()

  #leer la carpeta con los trajes dumpeados  
  dirlist = os.listdir("./member_model/suit")
  
  #leer diccionario de nombres desde un json (extraido usando sqlite), porque por alguna razon no me deja leer la base de datos directamente
  f = open('./m_dictionary.json')
  data = json.load(f)
  
  #para cada traje
  for cdir in dirlist:
    #filtrar la celda que contenga el id del traje (hay dos nombres, uno de la carta normal y otro de la idolizada)
    master_query = "select card_m_id, card_name from m_card_appearance WHERE card_m_id == " + cdir + " LIMIT 1"
    for (card_m_id, card_name) in masterdb.execute(master_query):
      #filtrar el json usando el id del nombre, que hace referencia al diccionario
      output_dict = [x for x in data if x['id'] == card_name.split(".")[1]]
      output_json = json.dumps(output_dict)
      
      #convertir el resultado a json y seleccionar el campo del nombre
      output_value = json.loads(output_json)[0]["message"]
      
      #filtrar los digitos especiales del nombre, que no soportan las carpetas
      result = re.sub('\W+',' ', output_value)
      
      #renombar carpeta del traje, al nombre de esta.
      try:
        print(result)
        #os.rename("./member_model/suit/" + cdir + "/", "./member_model/suit/" + result + "_" + cdir + "/")
      except Exception:
        pass


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
  test.set_defaults(func=test)
  
  args = parser.parse_args(sys.argv[1:])
  if 'func' not in args:
    parser.parse_args(['-h'])
  args.func(args)
