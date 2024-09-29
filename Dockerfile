# Use the official Python 3.12 image from Docker Hub
FROM python:3.12

RUN  apt-get update -y          && \
     apt-get upgrade -y         && \
     apt-get dist-upgrade -y    && \
     apt-get -y autoremove      && \
     apt-get clean              && \
     apt-get install -y p7zip      \
             p7zip-full            \
             unace                 \
             zip                   \
             unzip                 \
             xz-utils              \
             sharutils             \
             uudeview              \
             mpack                 \
             arj                   \
             cabextract            \
             file-roller           \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./dist /app

# Install any needed packages specified in awsrequirements.txt
RUN sed -i '/boto/d' requirements.txt                                                                         && \
    pip install -r requirements.txt --platform manylinux2014_x86_64 --target /app/package --only-binary=:all: && \
    find package/ -name "*.pyc" -delete                                                                       && \
    find package/ -name "__pycache__" -delete
