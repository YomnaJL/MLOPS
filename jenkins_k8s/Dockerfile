FROM jenkins/jenkins:lts

USER root

# 1. Installer les outils de base et PYTHON (Indispensable pour vos tests)
RUN apt-get update && apt-get install -y \
    lsb-release \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# 2. Installer Docker CLI (Version officielle pour éviter les conflits)
RUN curl -fsSLo /usr/share/keyrings/docker-archive-keyring.asc \
  https://download.docker.com/linux/debian/gpg
RUN echo "deb [arch=$(dpkg --print-architecture) \
  signed-by=/usr/share/keyrings/docker-archive-keyring.asc] \
  https://download.docker.com/linux/debian \
  $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
RUN apt-get update && apt-get install -y docker-ce-cli

# 3. Installer Kubernetes CLI (kubectl) - Votre partie était correcte
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    rm kubectl

# 4. Installer Docker Compose V2 (Plus moderne)
RUN mkdir -p /usr/libexec/docker/cli-plugins/
RUN curl -SL https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-linux-x86_64 -o /usr/libexec/docker/cli-plugins/docker-compose
RUN chmod +x /usr/libexec/docker/cli-plugins/docker-compose

# 5. Créer un alias pour 'python'
RUN ln -s /usr/bin/python3 /usr/bin/python

# On revient à l'utilisateur Jenkins
USER jenkins

# Installer les plugins Jenkins utiles au démarrage
RUN jenkins-plugin-cli --plugins "blueocean docker-workflow kubernetes-cli"
# On ajoute 'json-path-api' et 'token-macro' explicitement pour éviter le bug de dépendance
RUN jenkins-plugin-cli --plugins "blueocean docker-workflow kubernetes-cli json-path-api token-macro workflow-aggregator git"