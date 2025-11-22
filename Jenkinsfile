pipeline {
    agent any
    
    environment {
        IMAGE_NAME = "umbrella-app-vulnerable"
        // Al llamar a tu carpeta "umbrella", Docker Compose crea la red así:
        // nombrecarpeta_nombrered
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
                    // Limpiar contenedor previo si existe
                    sh "docker rm -f ${IMAGE_NAME}-test || true"
                    
                    // Desplegar en la red compartida para que ZAP lo vea
                    sh "docker run -d --network ${NETWORK_NAME} --name ${IMAGE_NAME}-test ${IMAGE_NAME}"
                }
            }
        }

        stage('3. Security Scan (OWASP ZAP)') {
            steps {
                script {
                    echo '--- Ejecutando DAST con OWASP ZAP ---'
                    // ZAP ataca al contenedor usando su nombre de red
                    sh """
                    docker run --rm --network ${NETWORK_NAME} \
                    -v ${WORKSPACE}:/zap/wrk/:rw \
                    -t zaproxy/zap-stable zap-baseline.py \
                    -t http://${IMAGE_NAME}-test:5000 \
                    -r zap_report.html || true
                    """
                }
            }
            post {
                always {
                    // Publicar reporte HTML
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
                    
                    // Despliegue final.
                    // Nombre 'umbrella-prod' coincide con prometheus.yml
                    sh "docker run -d --restart always --network ${NETWORK_NAME} --name umbrella-prod -p 5000:5000 ${IMAGE_NAME}"
                }
            }
        }
    }
}
