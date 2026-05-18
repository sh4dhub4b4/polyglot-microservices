# 🐳 Docker Important Commands

## 🔹 Running containers দেখতে

```bash id="g2b9bh"
docker ps
```

সব running container দেখাবে।

---

## 🔹 সব container দেখতে (stopped সহ)

```bash id="zkv6x4"
docker ps -a
```

---

## 🔹 Docker images দেখতে

```bash id="c9m1q0"
docker images
```

---

## 🔹 Container logs দেখতে

```bash id="owf5ht"
docker logs <container_id>
```

Live logs:

```bash id="f9m1f6"
docker logs -f <container_id>
```

---

## 🔹 Container এর ভিতরে ঢুকতে

```bash id="6ylz3w"
docker exec -it <container_id> bash
```

Alpine হলে:

```bash id="7m0kh7"
docker exec -it <container_id> sh
```

---

## 🔹 Container stop/start/restart

Stop:

```bash id="f2f1dz"
docker stop <container_id>
```

Start:

```bash id="5q4xow"
docker start <container_id>
```

Restart:

```bash id="4f1g5j"
docker restart <container_id>
```

---

## 🔹 Container delete

```bash id="qq5f53"
docker rm <container_id>
```

Force delete:

```bash id="jlwm0f"
docker rm -f <container_id>
```

---

## 🔹 Image delete

```bash id="i6ldqj"
docker rmi <image_id>
```

---

## 🔹 Build Docker image

```bash id="uxkq17"
docker build -t myapp .
```

---

## 🔹 Run container

```bash id="7y0fsk"
docker run -p 8080:8080 myapp
```

Detached mode:

```bash id="g3nuh1"
docker run -d -p 8080:8080 myapp
```

---

# ☸️ Kubernetes (`kubectl`) Important Commands

---

# 🔹 Cluster info

```bash id="6d3j2v"
kubectl cluster-info
```

---

# 🔹 Nodes দেখতে

```bash id="th44eo"
kubectl get nodes
```

Detailed:

```bash id="lm2c6u"
kubectl get nodes -o wide
```

---

# 🔹 Pods দেখতে

```bash id="5isf87"
kubectl get pods
```

সব namespace সহ:

```bash id="m9w2be"
kubectl get pods -A
```

Detailed:

```bash id="v3k6j4"
kubectl get pods -o wide
```

Live watch:

```bash id="z5o0f1"
kubectl get pods -w
```

---

# 🔹 Pod details

```bash id="fw1q8v"
kubectl describe pod <pod_name>
```

---

# 🔹 Pod logs

```bash id="sl5t2m"
kubectl logs <pod_name>
```

Live:

```bash id="fxh9m4"
kubectl logs -f <pod_name>
```

---

# 🔹 Pod এর ভিতরে ঢুকতে

```bash id="h0h9yh"
kubectl exec -it <pod_name> -- bash
```

Alpine:

```bash id="h3md7l"
kubectl exec -it <pod_name> -- sh
```

---

# 🔹 Deployment দেখতে

```bash id="v4gl47"
kubectl get deployments
```

---

# 🔹 Services দেখতে

```bash id="fw3h6r"
kubectl get svc
```

---

# 🔹 YAML apply করা

```bash id="8pj6uh"
kubectl apply -f deployment.yaml
```

Folder:

```bash id="x7e3jj"
kubectl apply -f k8s/
```

---

# 🔹 Resource delete করা

```bash id="k7x4ij"
kubectl delete -f deployment.yaml
```

বা:

```bash id="l7r8y1"
kubectl delete pod <pod_name>
```

---

# 🔹 Deployment restart

```bash id="w6m2yt"
kubectl rollout restart deployment <deployment_name>
```

---

# 🔹 Deployment status

```bash id="0p5k4v"
kubectl rollout status deployment <deployment_name>
```

---

# 🔹 Scale pods

```bash id="y4v2nm"
kubectl scale deployment myapp --replicas=3
```

---

# 🔹 Current context দেখতে

```bash id="vg7m2o"
kubectl config current-context
```

সব context:

```bash id="fz5q9n"
kubectl config get-contexts
```

Switch:

```bash id="g2s8xq"
kubectl config use-context <context_name>
```

---

# 🔹 Namespace commands

সব namespace:

```bash id="q2z7u9"
kubectl get ns
```

Specific namespace:

```bash id="j4m0eg"
kubectl get pods -n default
```

---

# 🔥 Extremely Useful Debug Commands

## Events দেখতে

```bash id="v1s4iw"
kubectl get events
```

---

## Resource usage

```bash id="g8u7q0"
kubectl top pods
```

```bash id="v9w5m3"
kubectl top nodes
```

---

# 🚀 Most Used Workflow

## Docker

```bash id="u2d8jg"
docker build -t myapp .
docker run -d -p 8080:8080 myapp
docker ps
docker logs -f <id>
```

---

## Kubernetes

```bash id="x4f2pu"
kubectl apply -f k8s/
kubectl get pods
kubectl logs -f <pod>
kubectl describe pod <pod>
kubectl get svc
```
