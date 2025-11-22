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
              sh 'docker network create umbrella_umbrella-net || true'
        
              echo '--- Desplegando entorno de pruebas ---'
              sh "docker rm -f ${IMAGE_NAME}-test || true"
        
              // lanzar la app
              sh "docker run -d --network umbrella_umbrella-net --name ${IMAGE_NAME}-test ${IMAGE_NAME}"
        
              // Esperar y comprobar que el contenedor responde por nombre desde un contenedor temporal (retry)
              echo '--- Comprobando resolución y salud (retry 10x) ---'
              sh '''
              for i in $(seq 1 10); do
                docker run --rm --network umbrella_umbrella-net curlimages/curl:8.2.1 -sS --max-time 5 http://${IMAGE_NAME}-test:5000/ && { echo "OK"; exit 0; } || echo "Intento $i: no disponible, esperando 3s" && sleep 3
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
        
              // arreglar permisos del volumen (asegurar que uid 1000 pueda escribir)
              // usamos un contenedor temporal para chown dentro del volumen:
              sh "docker run --rm -v zap-vol:/zap/wrk busybox sh -c 'chmod -R 0777 /zap/wrk || chown -R 1000:1000 /zap/wrk || true'"
        
              echo '--- Ejecutando DAST con OWASP ZAP (run as default user) ---'
              // Ejecuta ZAP. ejecutar normalmente; si sigues con problemas de permisos puedes añadir --user root
              sh """
              docker run --name zap-scanner --network umbrella_umbrella-net \
                -v zap-vol:/zap/wrk \
                -t zaproxy/zap-stable zap-baseline.py \
                -t http://${IMAGE_NAME}-test:5000 \
                -r zap_report.html || true
              """
        
              echo '--- Intentando extraer reporte del volumen de forma segura ---'
              // Copiamos desde el volumen a workspace con un contenedor temporal que hace el cp (evita docker cp directo)
              sh """
              docker run --rm -v zap-vol:/zap/wrk -v \$(pwd):/out busybox sh -c 'if [ -f /zap/wrk/zap_report.html ]; then cp /zap/wrk/zap_report.html /out/; else echo \"No report generated\"; fi'
              """
        
              // limpieza
              sh "docker rm -f zap-scanner || true"
              sh "docker volume rm zap-vol || true"
            }
          }
          post {
            always {
              publishHTML target: [
                allowMissing: true,            // <-- importante: permitir missing para no romper el job si no se generó el informe
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: '.',
                reportFiles: 'zap_report.html',
                reportName: 'OWASP ZAP Security Report'
              ]
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
