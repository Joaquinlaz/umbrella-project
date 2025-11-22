pipeline {
    agent any
    
    environment {
        IMAGE_NAME = "umbrella-app-vulnerable"
        // Asegúrate que esta red exista, o que docker-compose la haya creado.
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
              // crea la red si no existe (no falla si ya existe)
              sh "docker network create ${NETWORK_NAME} || true"
        
              echo '--- Desplegando entorno de pruebas ---'
              sh "docker rm -f ${IMAGE_NAME}-test || true"
        
              // lanzar la app
              sh "docker run -d --network ${NETWORK_NAME} --name ${IMAGE_NAME}-test ${IMAGE_NAME}"
        
              // Esperar y comprobar que el contenedor responde por nombre desde un contenedor temporal (retry)
              echo '--- Comprobando resolución y salud (retry 10x) ---'
              sh '''
              for i in $(seq 1 10); do
                docker run --rm --network ${NETWORK_NAME} curlimages/curl:8.2.1 -sS --max-time 5 http://${IMAGE_NAME}-test:5000/ && { echo "OK"; exit 0; } || echo "Intento $i: no disponible, esperando 3s" && sleep 3
              done
              echo "ERROR: servicio en ${IMAGE_NAME}-test no responde"; exit 1
              '''
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
        
              // asegurar permisos en el volumen (intento)
              sh "docker run --rm -v zap-vol:/zap/wrk busybox sh -c 'chmod -R 0777 /zap/wrk || true'"
        
              echo '--- Ejecutando DAST con OWASP ZAP (baseline) ---'
              // Ejecutar el contenedor y dejarlo en estado terminado/exists para copiar
              // NOTA: no eliminamos zap-scanner aquí.
              sh """
              docker run --name zap-scanner --network ${NETWORK_NAME} \
                -v zap-vol:/zap/wrk \
                -t zaproxy/zap-stable zap-baseline.py \
                  -t http://${IMAGE_NAME}-test:5000 \
                  -r zap_report.html \
                  -J zap_out.json || true
              """
              // En este punto el contenedor puede haber terminado (exited) o seguir, pero existe.
            }
          }
        }
        
        stage('3b. Collect ZAP artifacts (copy from container)') {
          steps {
            script {
              echo '--- Intentando copiar desde el contenedor zap-scanner (docker cp) ---'
              sh 'rm -rf zap-report || true'
              sh 'mkdir -p zap-report'
        
              // 1) Si existe el contenedor, intentamos docker cp
              sh """
              if docker inspect zap-scanner >/dev/null 2>&1; then
                echo "Contenedor zap-scanner existe: intentando docker cp zap-scanner:/zap/wrk -> ./zap-report"
                docker cp zap-scanner:/zap/wrk/. ./zap-report 2>/dev/null || echo "docker cp no copió nada de /zap/wrk (falló o vacío)"
              else
                echo "Contenedor zap-scanner NO existe."
              fi
              """
        
              // 2) Si docker cp anterior no produjo archivos, fallback a copiar desde volumen
              sh """
              if [ -z "$(ls -A zap-report 2>/dev/null)" ]; then
                echo "zap-report vacío, intentando fallback: copiar desde volumen zap-vol"
                docker run --rm -v zap-vol:/zap/wrk -v \$(pwd)/zap-report:/out busybox sh -c 'cp -a /zap/wrk/. /out/ || true'
              else
                echo "docker cp produjo archivos."
              fi
              """
        
              // 3) Si sigue vacío, inspeccionamos dentro del contenedor para ver rutas
              sh """
              if [ -z "$(ls -A zap-report 2>/dev/null)" ]; then
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
              sh 'echo \"--- listado zap-report ---\"'
              sh 'ls -la zap-report || true'
              sh 'echo \"--- primeras 120 lineas de zap-report/zap_report.html si existe ---\"'
              sh 'head -n 120 zap-report/zap_report.html || echo \"zap_report.html no existe o está vacío\"'
            }
          }
          post {
            always {
              // Archivar para descargar desde UI
              archiveArtifacts artifacts: 'zap-report/**', allowEmptyArchive: true
        
              // Publicar HTML desde el directorio que ahora sí contendrá los assets (si existen)
              publishHTML target: [
                allowMissing: true,               // mientras estabilizamos, permitimos missing
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'zap-report',
                reportFiles: 'zap_report.html',
                reportName: 'OWASP ZAP Security Report'
              ]
        
              // Limpieza: eliminar contenedor y volumen (comentar si quieres conservarlos para debugging)
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
