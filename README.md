# Crypto-Copy-Trader
Copy trading tool for cryptocurrencies - written in Python & Flask
<br/> Makes you copy high-performing masters without doing any effort

# Intro
bot used to make a mass buying or selling of identical bots to do basic copy trading. 

#### Supported Exchanges
- Binance Spot
- Bitmex
- Bitmex Testnet

# Installation and Launch

1. Downland and install requirements
    ``` 
    git clone https://github.com/MohammedRashad/Crypto-Copy-Trader.git
    cd Crypto-Copy-Trader
    pip install -r requirements.txt
    cp ./config_files/config-sample.json ./config_files/config.json
    ```
2. Configure `config.json`
    - Open `./config_files/config.json` in text editor and paste your api keys and secrets to master and slaves 
    - Possible values for a variable `exchange_name` you can find in folder ExchangeInterfaces. 

3. Run `python api.py`
     
4. Open GUI
    - go to http://127.0.0.1:5000/ or http://0.0.0.0:5000/
    - click `Run` button
    - see log in terminal or in file `logs/cct.log` 
    - when will you see message `Launch complete` you can place the orders
    
    
# Installation with Docker

1. Build Docker container

```
docker build -t crypto-copy-trader .
```

2. Run first Docker container

```
docker run --publish 8000:5000 --detach --name crypto-copy-trader crypto-copy-trader
```

# Features
- Database SQLite
- Slave-Master Configuration
- Copy active orders on launch
- WebUI
- Flask API
- All orders Supported
- Adding slaves in realtime
- Ratio for not similar accounts 
- Built with bootstrap

# Known Bugs
- Add and delete slaves buttons not working with new config file. So need to fill `config.json` manually
- database is not related with `config.json`
- Bitmex working only with `XBTUSD` and `ETHUSD` pairs now
- https://github.com/MohammedRashad/Crypto-Copy-Trader/issues/53 (environment python 3.8.x)
 
 Please [open an issue](https://github.com/MohammedRashad/Crypto-Copy-Trader/issues/new) to help us fix any bugs or request features if needed.
 

# Contributors 

Thanks to everyone trying to help, special thanks for [NickPius
](https://github.com/mokolotron) for multiple patches.

Contact me if you want to join as a contributor. 

# License
Apache 2.0 License
