"""
Run script for the Astra Authentication Flask application.
PROTOTYPE MODE: Relaxed security for multi-browser, multi-port testing.
"""
import os
import sys

# Add the parent directory to the path so imports work correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from asta_authentication.app import app, socketio

if __name__ == '__main__':
    # Allow custom port via command line or environment
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() in ["true", "1"]
    
    print("=" * 70)
    print("🚀 ASTRA AUTHENTICATION SERVER - PROTOTYPE MODE")
    print("=" * 70)
    print(f"📍 Local:    http://127.0.0.1:{port}")
    print(f"📍 Network:  http://0.0.0.0:{port}")
    print(f"🔧 Debug:    {debug_mode}")
    print(f"⚠️  Security: RELAXED (prototype only - not for production)")
    print("=" * 70)
    print(f"💡 To run on different port: python run.py <port>")
    print(f"   Example: python run.py 5001")
    print("=" * 70)
    
    # Bind to 0.0.0.0 to allow access from other devices/browsers
    socketio.run(app, debug=debug_mode, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)
