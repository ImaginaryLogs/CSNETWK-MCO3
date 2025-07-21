# CSNETWK-MCO3

![Static Badge](https://img.shields.io/badge/AY2425--T3-CSNETWK-red)

Link to the [Kanban Board](https://github.com/users/ImaginaryLogs/projects/2)

> [!IMPORTANT]
>
> Structure of the code:
>
>```txt
>docs/
> ├── CSNETWK MP Rubric.pdf
> │
> ├── CSNETWK MP RFC.pdf
> │
> └── TaskToDo.md
>src/
> ├── __init__.py
> │
> ├── config/                 <--: Configs
> │   └── ...
> ├── game/                   <--: Game state, player assets
> │   └── ...
> ├── manager/                <--: Core/Controller/Managers
> │   └── ...
> ├── protocol/               <--: Protocol and Type Definitions
> │   ├── ... 
> │   │
> │   └── types/   
> │       ├── games
> │       │
> │       └── messages
> ├── ui                      <--: UI/Terminal/View
> │   └── ...
> └── utils/                  <--: Helper files
>     └── ...
> tests/
> ├── __init__.py
> │
> ├── manager
> │   └── ...
> ├── network
> │   └── ...
> └── protocol
>     └── ...
> pyproject.toml
> __init__.py
> README.md
>```
>

## Installation

`pip install -r requirements.txt`

`pip install -e .`

`poetry install`

`poetry add <your-library-to-add>`

Running the server `poetry run python src/manager/main.py`

## Testing

`poetry install pytest`

`poetry run pytest`
