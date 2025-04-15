#!/bin/bash

# CONFIG
DOCKER_USERNAME="masterdann"
IMAGE_NAME="demoshift-web"
IMAGE_TAG="v1"  # Change this when needed
# Step 1: check u have all prerequisities (Docker installed, kubernets(minikube or VM), docker hub, python flask using SQLalchemy, kubectl)
#echo "⏳ Starting Kubernetes cluster..."


# Step 2: Build Docker image
#echo "🐳 Building Docker image..."
#docker build -t $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG .

# Step 3: Push to Docker Hub
#echo "📤 Pushing image to Docker Hub..."
#docker push $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG

# Step 4: Update deployment YAML 
# You can hardcode the image in the YAML instead
#in flask-app-deployment.yml, change image: masterdann/demoshift-web:XXXX to image: masterdann/demoshift-web:IMAGE TAG

# Step 5: Apply all Kubernetes manifests
#echo "📦 Applying Kubernetes configurations..."
#kubectl apply -f kubernetes/

# Step 6: Wait for pods to be ready
#echo "⏳ Waiting for pods to become ready..."
#ubectl wait --for=condition=ready pod -l app=flask-app --timeout=60s

# Step 7: Port-forward to localhost:8080
#echo "🌐 Port forwarding to http://localhost:8080"
#echo "🚀 Deployment complete! Press Ctrl+C to stop port forwarding."
kubectl port-forward service/flask-app-service 8080:80