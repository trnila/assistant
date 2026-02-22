# assistant
[Lunch menu](https://trnila.eu/lunch)

## VS Code
1. install `Dev Containers` extension in VS Code
2. press `Ctrl+Shift+P` and search for `Reopen in container`
3. press `Ctrl+Shift+P`, search for `Run task` and select `Run all`
4. open [http://localhost:5173/](http://localhost:5173/) in your browser

## Local setup
Install and start redis server for caching.

```sh
$ uv run prek install

# parse restaurant from CLI
$ uv run lunches.py bistroin

# start API server
$ uv run fastapi dev

# install frontend
$ cd frontend
$ yarn install
$ yarn run dev
```
