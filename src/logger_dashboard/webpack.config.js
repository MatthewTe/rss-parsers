const path = require('path');

module.exports = {
    devtool: 'eval-source-map',
    entry: {
        index: './src/index.ts',
        service_handshake: './src/microservice_status_check.ts' 
    },
    module: {
        rules: [
            {
                test: /\.ts$/,
                use: 'ts-loader',
                include: [path.resolve(__dirname, "src")]
            }, 
            {
                test: /\.css$/i,
                include: path.resolve(__dirname, 'src'),
                use: ['style-loader', 'css-loader', 'postcss-loader'],
            }
        ]
    },
    resolve: {
        extensions: ['.ts', '.js', ".css"]
    },
    output: {
        publicPath: 'public',
        filename: '[name].bundle.js',
        path: path.resolve(__dirname, "public")

    }
}