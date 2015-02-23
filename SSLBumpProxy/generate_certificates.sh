#!/bin/sh

openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/CN=SimpleHTTPProxy CA"
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=www.example.com"
openssl x509 -req -days 3650 -CA ca.crt -CAkey ca.key -set_serial 1 -in server.csr -out server.crt
rm server.csr
mkdir dynamic/
