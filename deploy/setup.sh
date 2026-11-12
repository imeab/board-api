#!/usr/bin/env bash
# EC2(Ubuntu)에서 한 번 실행하면 Docker 설치 → 코드 받기 → .env 생성 → 서버 실행까지 해줌
# 사용법: curl -fsSL https://raw.githubusercontent.com/imeab/board-api/main/deploy/setup.sh | bash
set -euo pipefail

REPO_URL="https://github.com/imeab/board-api.git"
APP_DIR="$HOME/board-api"

echo "== 1. Docker 설치 =="
if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
fi

echo "== 2. 코드 받기 =="
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "== 3. .env 만들기 (처음 한 번만, 비밀번호/키는 랜덤 생성) =="
if [ ! -f .env ]; then
    DB_PASSWORD=$(openssl rand -hex 16)
    JWT_KEY=$(openssl rand -base64 64 | tr -d '\n')
    cat > .env <<EOF
POSTGRES_PASSWORD=${DB_PASSWORD}
JWT_SECRET_KEY=${JWT_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=60
EOF
    chmod 600 .env
fi

echo "== 4. 실행 =="
sudo docker compose up -d --build

echo "== 5. 상태 확인 =="
for i in $(seq 1 30); do
    if curl -fs http://localhost/health >/dev/null; then
        PUBLIC_IP=$(curl -fs https://checkip.amazonaws.com || echo "<퍼블릭 IP>")
        echo ""
        echo "배포 완료!  Swagger: http://${PUBLIC_IP}/docs"
        exit 0
    fi
    sleep 2
done
echo "서버가 아직 준비되지 않았습니다. 로그 확인: sudo docker compose logs api"
exit 1
