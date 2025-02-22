# Use official Python image as base
FROM python:3.11

# Set the working directory in the container
WORKDIR /hms

# Copy the project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port Django runs on
EXPOSE 8000

# Run Gunicorn server
CMD ["gunicorn", "--workers=3", "--bind", "0.0.0.0:8000", "hospital_management.wsgi:application"]
