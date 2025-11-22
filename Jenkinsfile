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
                    // SOLUCIÓN 1: Esperar a que el contenedor de prueba esté listo
                    sh "sleep 20"

                    echo '--- Ejecutando DAST con OWASP ZAP ---'
                    
                    // Limpieza preventiva por si un escaneo anterior falló
                    sh "docker rm -f zap-scanner || true"

                    // SOLUCIÓN 2: Ejecutar ZAP SIN volúmenes (-v) para evitar errores de permisos.
                    // - Le damos un nombre fijo (--name zap-scanner)
                    // - Quitamos el --rm para que el contenedor no se borre solo al terminar
                    // - El '|| true' asegura que el pipeline continúe aunque encuentre vulnerabilidades
                    sh """
                    docker run --name zap-scanner --network ${NETWORK_NAME} \
                    -t zaproxy/zap-stable zap-baseline.py \
                    -t http://${IMAGE_NAME}-test:5000 \
                    -r zap_report.html || true
                    """

                    echo '--- Extrayendo reporte del contenedor ---'
                    // TRUCO: Copiamos el reporte desde adentro del contenedor hacia Jenkins
                    sh "docker cp zap-scanner:/zap/wrk/zap_report.html ./zap_report.html"
                    
                    // Ahora sí borramos el contenedor de escaneo
                    sh "docker rm -f zap-scanner"
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
