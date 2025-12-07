# ACOSlab2

## Использование
- #### Скачать исходный код.
```shell
git clone https://github.com/pkhlunev/ACOSlab2.git
cd ACOSlab2
```
- #### Запустить `server.py`. 
###### Пример:
```shell
chmod +x server.py
./server.py -h
./server.py -p tfile -i 0.5
```
- #### Запустить `client.py` с таким же `--path` (`-p`), чтобы они общались между собой. 
###### Пример:
```shell
chmod +x client.py
./client.py -h
./server.py -p tfile -i 0.5 -t 5.0
```
- #### Писать в интерактивный shell `client.py` payload. Сервер принимает только `ping` как правильный payload. При неправильном payload выдаст ошибку bad_request.