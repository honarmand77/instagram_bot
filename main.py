from app import create_app
import os

def run_dashboard():
    """اجرای داشبورد وب"""
    # ایجاد پوشه templates اگر وجود ندارد
    if not os.path.exists('app/templates'):
        os.makedirs('app/templates')
    
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == "__main__":
    run_dashboard()