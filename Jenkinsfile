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
                    echo '--- Desplegando entorno de pruebas ---'
                    sh "docker rm -f ${IMAGE_NAME}-test || true"
                    
                    // Desplegar la app de prueba
                    sh "docker run -d --network ${NETWORK_NAME} --name ${IMAGE_NAME}-test ${IMAGE_NAME}"
                }
            }
        }

        stage('3. Security Scan (OWASP ZAP)') {
            steps {
                script {
                    echo '--- Esperando que la aplicación inicie (DNS propagation) ---'
                    sh "sleep 20"

                    echo '--- Preparando entorno ZAP ---'
                    // 1. Limpieza previa
                    sh "docker rm -f zap-scanner || true"
                    sh "docker volume rm zap-vol || true"

                    // 2. Crear un volumen Docker temporal. 
                    // Esto satisface el requisito de ZAP de tener algo montado, sin usar rutas de Windows.
                    sh "docker volume create zap-vol"

                    echo '--- Ejecutando DAST con OWASP ZAP ---'
                    // 3. Ejecutar ZAP montando el volumen creado (-v zap-vol:/zap/wrk)
                    sh """
                    docker run --name zap-scanner --network ${NETWORK_NAME} \
                    -v zap-vol:/zap/wrk \
                    -t zaproxy/zap-stable zap-baseline.py \
                    -t http://${IMAGE_NAME}-test:5000 \
                    -r zap_report.html || true
                    """

                    echo '--- Extrayendo reporte del contenedor ---'
                    // 4. Copiamos el reporte. Docker es listo y sabe leer del volumen a través del contenedor.
                    sh "docker cp zap-scanner:/zap/wrk/zap_report.html ./zap_report.html"
                    
                    // 5. Limpieza final
                    sh "docker rm -f zap-scanner"
                    sh "docker volume rm zap-vol"
                }
            }
            post {
                always {
                    publishHTML target: [
                        allowMissing: false,
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
