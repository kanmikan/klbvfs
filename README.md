# LLSIFAS KLBVFS EXPERIMENTAL TOOLS
conjunto de herramientas experimentales para extraer y ordenar los datos sacados del juego, scripts experimentales para aprender como funciona el vfs del sifas, etc.

![tools.py chu 101 mikan_models](https://images2.imgbox.com/81/f4/HwQTc7Bn_o.png)

![tools.py test](https://images2.imgbox.com/e3/0c/Di3Y8YU6_o.png)

## TODO
- [x] extraccion y ordenamiento de stages
- [x] comando para extraer stages filtrado por generacion/subunidad
- [ ] (funcion decrypt) comprobar que el archivo existente no sea un placeholder de 0kb y reescribir en tal caso
- [ ] copiar los packs acb/awb de m_asset_sound junto con los stages ordenados
- [ ] actualizar automáticamente los packs, masterdata.db y assets*.db con las nuevas claves sacadas del shared_prefs, directamente del dump.

## CHEATSHEET DE COMANDOS (NO ES UN PROCEDIMIENTO)
- adb pull /sdcard/Android/data/com.klab.lovelive.allstars.global com.klab.lovelive.allstars.global
- adb backup -shared com.klab.lovelive.allstars.global -f sifas_data.ab
- java -jar abe.jar sifas_data.ab sifas_data.tar
- ./klbvfs.py decrypt *.db_*.db
- ./klbvfs.py dump --types=member_model

# INFORMACION ORIGINAL DE KLBVFS
This is a proof-of-concept implementation of klab's encrypted sqlite3 vfs (virtual file system). It can be used to query encrypted databases in your
`/data/data/com.klab.lovelive.allstars/files/files` directory

It assumes your directory structure is the same as it would be on your
android device to extract your master key from `shared_prefs` . so you
must dump your `/data/data` directory as is, or run this directly on your
phone.

To get all the files in the right directory, get all the `pkg` files and `.db.*` files in one folder, then copy the `klbvfs.py` file to that directory.

# Usage
You need python3 and pip installed

If you have python venv:

```sh
python3 -m venv env
source env/bin/activate
```

Then install dependencies

```c
python3 -m pip install -r requirements.txt
```

Now you can use it

```
./klbvfs.py query masterdata.db_* "select sql from sqlite_master;"
./klbvfs decrypt *.db_*.db
./klbvfs.py --help
./klbvfs.py dump [--types [[...]]] [directories [directories ...]]
```

Example (while in the directory with all the `pkg` folders):

```
./klbvfs.py dump --types=member_model
```

This also registers a python codec for klbvfs which can be used to decrypt
like so

```python
key = sqlite_key('encrypted.db')
src = codecs.open('encrypted.db', mode='rb', encoding='klbvfs', errors=key)
dst = open('decrypted.db', 'wb+')
shutil.copyfileobj(src, dst)
```

# Future development
I'd like to actually make it dump all the `pkg*` files with correct names
and directory structure. the mapping between virtual paths and pkg dirs
is stored in these db's among other stuff
