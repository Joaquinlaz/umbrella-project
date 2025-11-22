pipeline {
    agent any

    environment {
        IMAGE_NAME = "umbrella-app-vulnerable"
        NETWORK_NAME = "umbrella_umbrella-net"
    }

    stages {
        stage('1. Build') {
            steps {
                script {
                    echo '--- Construyendo Imagen Docker ---'
                    sh "docker build -t ${IMAGE_NAME} ./app"
                }
            }
        }

        stage('2. Deploy to Test') {
            steps {
                script {
                    echo '--- Asegurando red Docker ---'
                    sh "docker network create ${NETWORK_NAME} || true"

                    echo '--- Desplegando entorno de pruebas ---'
                    sh "docker rm -f ${IMAGE_NAME}-test || true"
                    sh "docker run -d --network ${NETWORK_NAME} --name ${IMAGE_NAME}-test ${IMAGE_NAME}"

                    echo '--- Comprobando resolución y salud (retry 10x) ---'
                    // Usamos comillas dobles triples para poder usar variables ${} dentro del shell script fácilmente
                    sh """
                    for i in \$(seq 1 10); do
                        docker run --rm --network ${NETWORK_NAME} curlimages/curl:8.2.1 -sS --max-time 5 http://${IMAGE_NAME}-test:5000/ && { echo "OK"; exit 0; } || { echo "Intento \$i: no disponible, esperando 3s"; sleep 3; }
                    done
                    echo "ERROR: servicio en ${IMAGE_NAME}-test no responde"
                    exit 1
                    """
                }
            }
        }

        stage('3. Security Scan (OWASP ZAP)') {
            steps {
                script {
                    echo '--- Preparando entorno ZAP ---'
                    sh "docker rm -f zap-scanner || true"
                    sh "docker volume rm zap-vol || true"
                    sh "docker volume create zap-vol"

                    // Asegurar permisos en el volumen para que cualquier usuario pueda escribir
                    sh "docker run --rm -v zap-vol:/zap/wrk busybox sh -c 'chmod -R 0777 /zap/wrk || true'"

                    echo '--- Ejecutando DAST con OWASP ZAP (baseline) ---'
                    // Nota: || true al final evita que el pipeline falle si encuentra vulnerabilidades
                    sh """
                    docker run --name zap-scanner --network ${NETWORK_NAME} \
                    -v zap-vol:/zap/wrk \
                    -t zaproxy/zap-stable zap-baseline.py \
                    -t http://${IMAGE_NAME}-test:5000 \
                    -r zap_report.html \
                    -J zap_out.json || true
                    """
                    // NO borramos el contenedor aquí; lo necesitamos para el siguiente stage
                }
            }
        }

        stage('3b. Collect ZAP artifacts (docker cp fallback)') {
            steps {
                script {
                    echo '--- Preparando zap-report (limpio) ---'
                    sh 'rm -rf zap-report || true'
                    sh 'mkdir -p zap-report'

                    // 1) Intentar docker cp desde el contenedor
                    sh """
                    if docker inspect zap-scanner >/dev/null 2>&1; then
                        echo "Contenedor zap-scanner existe: intentando docker cp..."
                        docker cp zap-scanner:/zap/wrk/. ./zap-report 2>/dev/null || echo "docker cp falló o carpeta vacía"
                    else
                        echo "Contenedor zap-scanner NO existe."
                    fi
                    """

                    // 2) Fallback: copiar desde volumen si zap-report sigue vacío
                    sh """
                    if [ -z "\$(ls -A zap-report 2>/dev/null)" ]; then
                        echo "zap-report vacío, intentando fallback: copiar desde volumen zap-vol"
                        docker run --rm -v zap-vol:/zap/wrk -v \$(pwd)/zap-report:/out busybox sh -c 'cp -a /zap/wrk/. /out/ || true'
                    else
                        echo "El paso anterior (docker cp) funcionó."
                    fi
                    """

                    // 3) Debugging: Si sigue vacío, inspeccionamos rutas
                    sh """
                    if [ -z "\$(ls -A zap-report 2>/dev/null)" ]; then
                        echo "ALERTA: Aún vacío. Debugging rutas..."
                        if docker inspect zap-scanner >/dev/null 2>&1; then
                            echo "---- ls -la /zap/wrk (dentro del contenedor) ----"
                            docker exec zap-scanner sh -c 'ls -la /zap/wrk || true'
                            echo "---- Buscando zap_report.html ----"
                            docker exec zap-scanner sh -c 'find / -maxdepth 3 -type f -name "zap_report.html" || true'
                        fi
                    fi
                    """

                    // 4) Mostrar resultado final en logs
                    sh 'echo "--- Contenido final de carpeta zap-report ---"'
                    sh 'ls -la zap-report || true'
                }
            }
            post {
                always {
                    // Archivar artifacts para descarga desde la UI de Jenkins
                    archiveArtifacts artifacts: 'zap-report/**', allowEmptyArchive: true

                    // Publicar reporte HTML
                    publishHTML target: [
                        allowMissing: true, // Cambiar a false cuando sea estable
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'zap-report',
                        reportFiles: 'zap_report.html',
                        reportName: 'OWASP ZAP Security Report'
                    ]

                    // Limpieza final
                    sh "docker rm -f zap-scanner || true"
                    sh "docker volume rm zap-vol || true"
                }
            }
        }

        stage('4. Deploy to Prod (Monitoring)') {
            steps {
                script {
                    echo '--- Desplegando Producción ---'
                    sh "docker rm -f umbrella-prod || true"
                    sh "docker run -d --restart always --network ${NETWORK_NAME} --name umbrella-prod -p 5000:5000 ${IMAGE_NAME}"
                }
            }
        }
    }
}
