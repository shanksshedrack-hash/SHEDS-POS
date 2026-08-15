@echo off
REM AWS S3 Deploy Script for SHEDS POS
REM Usage: deploy-aws.bat

set BUCKET=danzona-pharm-nig-ltd-pos

echo Deploying SHEDS POS to S3 bucket: %BUCKET%
aws s3 mb s3://%BUCKET% --region us-east-1 2>nul
aws s3 sync . s3://%BUCKET% --delete --cache-control max-age=31536000 --exclude "*.bat" --exclude "*.md" --exclude "*.backup*" --exclude "temp_*"
aws s3 website s3://%BUCKET% --index-document sales.html

echo.
echo Upload complete.
echo Website URL: http://%BUCKET%.s3-website-us-east-1.amazonaws.com
echo For HTTPS, configure CloudFront in AWS Console.
pause