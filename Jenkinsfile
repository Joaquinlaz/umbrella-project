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
        
              // arreglar permisos del volumen (asegurar que uid 1000 pueda escribir)
              sh "docker run --rm -v zap-vol:/zap/wrk busybox sh -c 'chmod -R 0777 /zap/wrk || chown -R 1000:1000 /zap/wrk || true'"
        
              echo '--- Ejecutando DAST con OWASP ZAP (baseline) ---'
              // Generar HTML y JSON (diagnóstico)
              sh """
              docker run --name zap-scanner --network ${NETWORK_NAME} \
                -v zap-vol:/zap/wrk \
                -t zaproxy/zap-stable zap-baseline.py \
                -t http://${IMAGE_NAME}-test:5000 \
                -r zap_report.html \
                -J zap_out.json || true
              """
            }
          }
          post {
            always {
              // No publicamos aquí: vamos a copiar todo el contenido en el siguiente stage
              echo '--- ZAP scan finished (logs above) ---'
            }
          }
        }

        stage('3b. Collect ZAP artifacts') {
          steps {
            script {
              echo '--- Copiando TODO /zap/wrk (assets + html) al workspace -> zap-report ---'
              sh 'rm -rf zap-report || true'
              sh 'mkdir -p zap-report'

              // monta el volumen y copia todo su contenido al workspace (incluye subcarpetas)
              sh "docker run --rm -v zap-vol:/zap/wrk -v \$(pwd)/zap-report:/out busybox sh -c 'cp -a /zap/wrk/. /out/ || true'"

              // Mostrar lista y top del HTML para depuración inmediata
              sh 'echo \"--- Listado zap-report ---\"'
              sh 'ls -la zap-report || true'
              sh 'echo \"--- Primeras 120 líneas de zap-report/zap_report.html ---\"'
              sh 'head -n 120 zap-report/zap_report.html || echo \"zap_report.html no existe o está vacío\"'
            }
          }
          post {
            always {
              // Archivar todos los assets para poder descargarlos desde la UI del build
              archiveArtifacts artifacts: 'zap-report/**', allowEmptyArchive: true

              // Publicar el HTML (ahora apuntando al directorio con los assets)
              publishHTML target: [
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'zap-report',
                reportFiles: 'zap_report.html',
                reportName: 'OWASP ZAP Security Report'
              ]

              // limpieza del contenedor y volumen (si quieres mantener para debugging, comenta estas líneas)
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
