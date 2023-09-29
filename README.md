# assistant
[Lunch menu](https://trnila.eu/lunch)

## Local setup
Install and start redis server for caching.

```sh
$ pip install -r requirements.txt

# parse restaurant from CLI
$ ./lunches.py bistroin

# start API server
$ ./app.py

# install frontend
$ cd frontend
$ npm install
$ npm run dev
```
