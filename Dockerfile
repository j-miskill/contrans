# syntax=docker/dockerfile:1

# use an official Python image as the base
FROM python:3.12.5-bookworm

# set the working directory
WORKDIR /ds6600

# copy requirements file into working directory
COPY requirements.txt requirements.txt

# install dependencies using pip
RUN pip install -r requirements.txt

# expose port for jupyter lab
EXPOSE 8888

# jupyter lab file 
CMD ["jupyter", "lab","--ip=0.0.0.0","--allow-root", "--port=8888"]