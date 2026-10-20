import os
from flask import Flask, render_template, jsonify
from config import Config
from routes.api_routes import api_bp

def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    app.config.from_object(Config)

    # Register API routes
    app.register_blueprint(api_bp)

    @app.route('/')
    def dashboard():
        """Renders the Digital Twin Doctor Dashboard."""
        return render_template('index.html')

    @app.route('/metabolic-twin')
    def metabolic_twin():
        """Renders the Whole Body Metabolic Digital Twin Interface."""
        return render_template('metabolic_twin.html')

    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy',
            'application': 'Digital Twin Healthcare Platform 2026',
            'version': '1.0.0'
        })

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  Digital Twin Healthcare Platform 2026")
    print(f"  Doctor Dashboard: http://127.0.0.1:{port}/")
    print(f"  REST API Base:    http://127.0.0.1:{port}/api/")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=True)
