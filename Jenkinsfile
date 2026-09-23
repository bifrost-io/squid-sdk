// The platform catalog owns build inputs and the Harbor destination.
pipeline {
    agent none
    options { skipDefaultCheckout(true) }
    stages {
        stage('Build image') {
            when { branch 'firesquid' }
            steps {
                build job: '/bifrost/build/services', wait: true, propagate: true,
                    parameters: [
                        string(name: 'SOURCE_REPOSITORY', value: 'bifrost-io/squid-sdk'),
                        string(name: 'SOURCE_BRANCH', value: env.BRANCH_NAME)
                    ]
            }
        }
    }
}
