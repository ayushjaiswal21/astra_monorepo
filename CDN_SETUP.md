# CDN Setup Guide for AstraLearn

## Overview
This guide explains how to set up a CDN (Content Delivery Network) for your AstraLearn application to improve performance and reduce latency for users worldwide.

## Recommended CDN Providers

### 1. Cloudflare (Free tier available)
- Global CDN with DDoS protection
- Free SSL certificates
- Easy DNS management
- Setup: Point your domain's nameservers to Cloudflare

### 2. AWS CloudFront
- Highly scalable CDN
- Integration with AWS services
- Pay-as-you-go pricing
- Setup: Create distribution and configure origins

### 3. Google Cloud CDN
- Global load balancing
- Integration with Google Cloud
- Setup: Configure load balancer and CDN

## Configuration Steps

### 1. Environment Variables
Add these to your production .env file:

```bash
CDN_URL=https://cdn.yourdomain.com
USE_CDN=true
```

### 2. Static Files Collection
When deploying, collect static files to your CDN:

```bash
python manage.py collectstatic
```

### 3. Nginx Configuration
Update your Nginx config to proxy requests through CDN:

```nginx
# Proxy static files through CDN
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
    proxy_pass $cdn_url;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 4. DNS Configuration
Point your CDN subdomain to your server:

```
cdn.yourdomain.com -> your-server-ip
```

## Performance Benefits

- **Reduced Latency**: Files served from geographically closer servers
- **Bandwidth Savings**: Less load on your origin server
- **Better SEO**: Faster loading times improve search rankings
- **Improved UX**: Faster page loads for global users

## Monitoring

Monitor your CDN performance:
- Cache hit rates
- Response times by region
- Bandwidth usage
- Error rates

## Security Considerations

- Enable HTTPS on your CDN
- Configure proper cache headers
- Set up access controls if needed
- Monitor for DDoS attacks
