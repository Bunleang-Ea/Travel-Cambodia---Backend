#!/bin/bash

# Travel Cambodia Backend - Quick Smoke Test
# Run this to verify all endpoints are working
# Usage: bash scripts/test_automated.sh

API_URL="http://localhost:8000/api"
BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BOLD}=== Travel Cambodia Backend Smoke Test ===${NC}\n"

# Test 1: Health Check
echo -e "${BOLD}1. Health Check${NC}"
RESPONSE=$(curl -s "$API_URL/health/")
if echo "$RESPONSE" | grep -q "ok"; then
    echo -e "${GREEN}✓ PASS${NC} - Server is running\n"
else
    echo -e "${RED}✗ FAIL${NC} - Server not responding\n"
    exit 1
fi

# Test 2: API Schema
echo -e "${BOLD}2. API Schema${NC}"
RESPONSE=$(curl -s "$API_URL/schema/")
if echo "$RESPONSE" | grep -q "openapi\|swagger"; then
    echo -e "${GREEN}✓ PASS${NC} - OpenAPI schema available\n"
else
    echo -e "${RED}✗ FAIL${NC} - Schema not found\n"
fi

# Test 3: API Documentation
echo -e "${BOLD}3. API Documentation${NC}"
RESPONSE=$(curl -s "$API_URL/docs/")
if echo "$RESPONSE" | grep -q "SwaggerUI\|swagger"; then
    echo -e "${GREEN}✓ PASS${NC} - Swagger UI available\n"
else
    echo -e "${YELLOW}⚠ INFO${NC} - Swagger UI may not be available\n"
fi

# Test 4: Registration Endpoint
echo -e "${BOLD}4. User Registration${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/accounts/register/" \
  -H "Content-Type: application/json" \
  -d '{"email":"smoketest'$(date +%s)'@example.com","password":"TestPass123!","full_name":"Smoke Test","phone_number":"+1-555-1234"}')

if echo "$RESPONSE" | grep -q "token"; then
    echo -e "${GREEN}✓ PASS${NC} - User registration works"
    TOKEN=$(echo "$RESPONSE" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
    USER_EMAIL=$(echo "$RESPONSE" | grep -o '"email":"[^"]*' | cut -d'"' -f4)
    echo -e "  Email: $USER_EMAIL"
    echo -e "  Token: ${TOKEN:0:20}...\n"
else
    echo -e "${RED}✗ FAIL${NC} - Registration failed"
    echo "  Response: $RESPONSE\n"
fi

# Test 5: Login Endpoint
echo -e "${BOLD}5. User Login${NC}"
if [ ! -z "$USER_EMAIL" ]; then
    RESPONSE=$(curl -s -X POST "$API_URL/accounts/login/" \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"$USER_EMAIL\",\"password\":\"TestPass123!\"}")
    
    if echo "$RESPONSE" | grep -q "token"; then
        echo -e "${GREEN}✓ PASS${NC} - Login works\n"
    else
        echo -e "${RED}✗ FAIL${NC} - Login failed\n"
    fi
else
    echo -e "${YELLOW}⚠ SKIP${NC} - Registration failed, skipping login test\n"
fi

# Test 6: Protected Endpoint (requires auth)
echo -e "${BOLD}6. Protected Endpoint (without token)${NC}"
RESPONSE=$(curl -s -X GET "$API_URL/accounts/me/")
if echo "$RESPONSE" | grep -q "credentials\|unauthorized\|Unauthorized"; then
    echo -e "${GREEN}✓ PASS${NC} - Endpoint properly protected\n"
else
    echo -e "${YELLOW}⚠ INFO${NC} - Endpoint may not be fully protected\n"
fi

# Test 7: Protected Endpoint (with token)
echo -e "${BOLD}7. Protected Endpoint (with token)${NC}"
if [ ! -z "$TOKEN" ]; then
    RESPONSE=$(curl -s -X GET "$API_URL/accounts/me/" \
      -H "Authorization: Token $TOKEN")
    
    if echo "$RESPONSE" | grep -q "email"; then
        echo -e "${GREEN}✓ PASS${NC} - Authentication works\n"
    else
        echo -e "${RED}✗ FAIL${NC} - Token not working\n"
    fi
else
    echo -e "${YELLOW}⚠ SKIP${NC} - No token available\n"
fi

# Test 8: Admin Endpoint Protection
echo -e "${BOLD}8. Admin Endpoint Protection${NC}"
if [ ! -z "$TOKEN" ]; then
    RESPONSE=$(curl -s -X GET "$API_URL/accounts/admin/users/" \
      -H "Authorization: Token $TOKEN")
    
    if echo "$RESPONSE" | grep -q "not allowed\|forbidden\|Forbidden"; then
        echo -e "${GREEN}✓ PASS${NC} - Admin endpoints protected\n"
    else
        echo -e "${YELLOW}⚠ INFO${NC} - Admin protection may vary\n"
    fi
else
    echo -e "${YELLOW}⚠ SKIP${NC} - No token available\n"
fi

# Test 9: Input Validation
echo -e "${BOLD}9. Input Validation (bad email)${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/accounts/register/" \
  -H "Content-Type: application/json" \
  -d '{"email":"invalid","password":"TestPass123!","full_name":"Test","phone_number":"+1-555-1234"}')

if echo "$RESPONSE" | grep -q "error\|invalid\|Email"; then
    echo -e "${GREEN}✓ PASS${NC} - Email validation works\n"
else
    echo -e "${YELLOW}⚠ INFO${NC} - Email validation may vary\n"
fi

# Summary
echo -e "${BOLD}=== Test Complete ===${NC}"
echo -e "${GREEN}✓ Smoke tests finished${NC}"
echo -e "\nFor comprehensive testing, use:"
echo -e "  ${BOLD}python manage.py test accounts --keepdb${RESET}\n"
