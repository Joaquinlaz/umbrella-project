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
                    sh "docker build -t ${env.IMAGE_NAME} ./app"
                }
            }
        }

        stage('2. Deploy to Test') {
            steps {
                script {
                    echo '--- Asegurando red Docker ---'
                    sh "docker network create ${env.NETWORK_NAME} || true"

                    echo '--- Desplegando entorno de pruebas ---'
                    sh "docker rm -f ${env.IMAGE_NAME}-test || true"
                    sh "docker run -d --network ${env.NETWORK_NAME} --name ${env.IMAGE_NAME}-test ${env.IMAGE_NAME}"

                    echo '--- Comprobando resolución y salud (retry 10x) ---'
                    // NOTA: escapamos los $ usados por la shell (\$) para que Groovy no los interprete
                    sh """
                    for i in \\$(seq 1 10); do
                      docker run --rm --network ${env.NETWORK_NAME} curlimages/curl:8.2.1 -sS --max-time 5 http://${env.IMAGE_NAME}-test:5000/ && { echo "OK"; exit 0; } || { echo "Intento \\$i: no disponible, esperando 3s"; sleep 3; }
                    done
                    echo "ERROR: servicio en ${env.IMAGE_NAME}-test no responde"
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

                    // asegurar permisos en el volumen
                    sh "docker run --rm -v zap-vol:/zap/wrk busybox sh -c 'chmod -R 0777 /zap/wrk || true'"

                    echo '--- Ejecutando DAST con OWASP ZAP (baseline) ---'
                    sh """
                    docker run --name zap-scanner --network ${env.NETWORK_NAME} \\
                      -v zap-vol:/zap/wrk \\
                      -t zaproxy/zap-stable zap-baseline.py \\
                        -t http://${env.IMAGE_NAME}-test:5000 \\
                        -r zap_report.html \\
                        -J zap_out.json || true
                    """
                    // El contenedor zap-scanner queda presente (exited) para copiar artefactos
                }
            }
        }

        stage('3b. Collect ZAP artifacts (copy from container)') {
            steps {
                script {
                    echo '--- Intentando copiar desde el contenedor zap-scanner (docker cp) ---'
                    sh 'rm -rf zap-report || true'
                    sh 'mkdir -p zap-report'

                    // 1) Intentar docker cp desde el contenedor
                    sh """
                    if docker inspect zap-scanner >/dev/null 2>&1; then
                      echo "Contenedor zap-scanner existe: intentando docker cp zap-scanner:/zap/wrk -> ./zap-report"
                      docker cp zap-scanner:/zap/wrk/. ./zap-report 2>/dev/null || echo "docker cp no copió nada de /zap/wrk (falló o vacío)"
                    else
                      echo "Contenedor zap-scanner NO existe."
                    fi
                    """

                    // 2) Fallback: copiar desde volumen si zap-report sigue vacío
                    // Escapamos \$(pwd) para que Groovy no lo procese
                    sh """
                    if [ -z "\\$(ls -A zap-report 2>/dev/null)" ]; then
                      echo "zap-report vacío, intentando fallback: copiar desde volumen zap-vol"
                      docker run --rm -v zap-vol:/zap/wrk -v \\$(pwd)/zap-report:/out busybox sh -c 'cp -a /zap/wrk/. /out/ || true'
                    else
                      echo "docker cp produjo archivos."
                    fi
                    """

                    // 3) Si sigue vacío, inspeccionar dentro del contenedor para ver rutas
                    sh """
                    if [ -z "\\$(ls -A zap-report 2>/dev/null)" ]; then
                      echo "Aún vacío: listando rutas dentro de zap-scanner para investigar..."
                      if docker inspect zap-scanner >/dev/null 2>&1; then
                        docker exec zap-scanner sh -c 'echo \"--- ls -la /zap\"; ls -la /zap || true'
                        docker exec zap-scanner sh -c 'echo \"--- ls -la /zap/wrk\"; ls -la /zap/wrk || true'
                        docker exec zap-scanner sh -c 'echo \"--- pwd; ls -la\"; pwd; ls -la || true'
                      else
                        echo "Contenedor zap-scanner no disponible para exec."
                      fi
                    fi
                    """

                    // 4) Mostrar lo copiado (si lo hay)
                    sh 'echo "--- listado zap-report ---"'
                    sh 'ls -la zap-report || true'
                    sh 'echo "--- primeras 120 lineas de zap-report/zap_report.html si existe ---"'
                    sh 'head -n 120 zap-report/zap_report.html || echo "zap_report.html no existe o está vacío"'
                }
            }
            post {
                always {
                    // Archivar artifacts para descarga desde la UI
                    archiveArtifacts artifacts: 'zap-report/**', allowEmptyArchive: true

                    // Publicar HTML (en modo tolerante mientras debuggeas)
                    publishHTML target: [
                      allowMissing: true,
                      alwaysLinkToLastBuild: true,
                      keepAll: true,
                      reportDir: 'zap-report',
                      reportFiles: 'zap_report.html',
                      reportName: 'OWASP ZAP Security Report'
                    ]

                    // Limpieza: eliminar contenedor y volumen (comentar si prefieres mantenerlos)
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
                    sh "docker run -d --restart always --network ${env.NETWORK_NAME} --name umbrella-prod -p 5000:5000 ${env.IMAGE_NAME}"
                }
            }
        }
    }
}
