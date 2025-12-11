Kindly refer ```report.pdf``` for all details.

```
.
├── ansible
│   ├── inventory.ini
│   ├── playbook.yml
│   ├── roles
│   │   ├── build_and_push_to_docker
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   ├── configure_kibana
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   ├── deploy_on_kubernetes
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   ├── install_docker
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   ├── install_kubernetes
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   ├── prepare_kubernetes
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   ├── set_up_workspace
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   ├── train_model
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   ├── update_system
│   │   │   └── tasks
│   │   │       └── main.yml
│   │   └── use_latest_model
│   │       └── tasks
│   │           └── main.yml
│   └── rotpot_vault.yml
├── app.py
├── data
│   ├── full_dataset.csv
│   ├── IMDB Dataset.csv.zip
│   ├── initial_movies.json
│   ├── initial_reviews.json
│   ├── train.csv
│   └── train.csv.dvc
├── docker
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── frontend.py
├── Jenkinsfile
├── kubernetes
│   ├── k8s-database.yaml
│   ├── k8s-ingress.yaml
│   ├── k8s-logging.yaml
│   └── templates
│       ├── backend.yaml.j2
│       └── frontend.yaml.j2
├── manage_data.py
├── notes.txt
├── problem_statement.pdf
├── report.pdf
├── requirements.txt
└── train.py
```
