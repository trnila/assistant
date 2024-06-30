# assistant
[Lunch menu](https://trnila.eu/lunch)

## Local setup
Install and start redis server for caching.

```sh
$ pip install pre-commit
$ pre-commit install

$ poetry install
$ poetry shell

# parse restaurant from CLI
$ ./lunches.py bistroin

# start API server
$ fastapi dev

# install frontend
$ cd frontend
$ yarn install
$ yarn run dev
```
