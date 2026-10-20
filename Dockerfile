# ==============================================================
# Samir AI Assistant - 24/7 Cloud Dockerfile
# تشغيل خادم سمير الذكي 24 ساعة في السحابة حتى لو كان جهازك مغلقاً
# ==============================================================

FROM python:3.12-slim

# منع بايثون من توليد ملفات pyc وضمان إخراج السجلات فوراً
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PORT=10000


WORKDIR /app

# تثبيت الحزم الأساسية للنظام
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# نسخ متطلبات المشروع وتثبيتها
COPY core_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كود الخادم وملفات الواجهة
COPY core_server /app
COPY samir.ico /app/samir.ico

# إنشاء مجلدات البيانات والوسائط
RUN mkdir -p /app/data /app/projects /app/data/sandbox /app/uploads

EXPOSE 10000

# تشغيل خادم سمير السحابي 24/7 عبر run_server.py
CMD ["python", "run_server.py"]


