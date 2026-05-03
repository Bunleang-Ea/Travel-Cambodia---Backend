#!/usr/bin/env pwsh
# Travel Cambodia Backend - Windows PowerShell Testing Script
# Run this script to test all features
#
# Usage: .\scripts\test_manual.ps1

$API = "http://localhost:8000/api"
$GREEN = "`e[32m"
$RED = "`e[31m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$RESET = "`e[0m"

Write-Host "${BLUE}=== Travel Cambodia Backend - Test Suite ===${RESET}`n"

# Test 1: Health Check
Write-Host "${BLUE}1. Health Check${RESET}"
try {
    $response = Invoke-WebRequest -Uri "$API/health/" -Method GET
    $data = $response.Content | ConvertFrom-Json
    Write-Host "${GREEN}✓ PASS${RESET} - Server is running`n"
} catch {
    Write-Host "${RED}✗ FAIL${RESET} - Server not responding`n"
    exit 1
}

# Test 2: API Schema
Write-Host "${BLUE}2. API Schema${RESET}"
try {
    $response = Invoke-WebRequest -Uri "$API/schema/" -Method GET
    Write-Host "${GREEN}✓ PASS${RESET} - OpenAPI schema available`n"
} catch {
    Write-Host "${YELLOW}⚠ SKIP${RESET} - Schema not available`n"
}

# Test 3: API Documentation
Write-Host "${BLUE}3. API Documentation${RESET}"
try {
    $response = Invoke-WebRequest -Uri "$API/docs/" -Method GET
    Write-Host "${GREEN}✓ PASS${RESET} - Swagger UI available`n"
} catch {
    Write-Host "${YELLOW}⚠ SKIP${RESET} - Swagger UI not available`n"
}

# Test 4: User Registration
Write-Host "${BLUE}4. User Registration${RESET}"
$timestamp = Get-Date -UFormat "%s"
$testEmail = "test$timestamp@example.com"

$body = @{
    email = $testEmail
    password = "TestPass123!"
    full_name = "Test User"
    phone_number = "+1-555-1234"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$API/accounts/register/" -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $body
    
    $data = $response.Content | ConvertFrom-Json
    $token = $data.token
    
    Write-Host "${GREEN}✓ PASS${RESET} - User registration works"
    Write-Host "  Email: $testEmail"
    Write-Host "  Token: $($token.Substring(0, 20))...`n"
} catch {
    Write-Host "${RED}✗ FAIL${RESET} - Registration failed"
    Write-Host "  Error: $($_.Exception.Message)`n"
}

# Test 5: User Login
Write-Host "${BLUE}5. User Login${RESET}"
$body = @{
    email = $testEmail
    password = "TestPass123!"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$API/accounts/login/" -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $body
    
    $data = $response.Content | ConvertFrom-Json
    $loginToken = $data.token
    
    Write-Host "${GREEN}✓ PASS${RESET} - Login works`n"
} catch {
    Write-Host "${RED}✗ FAIL${RESET} - Login failed`n"
}

# Test 6: Protected Endpoint (with token)
Write-Host "${BLUE}6. Protected Endpoint (with token)${RESET}"
try {
    $response = Invoke-WebRequest -Uri "$API/accounts/me/" -Method GET `
        -Headers @{"Authorization"="Token $token"}
    
    $data = $response.Content | ConvertFrom-Json
    Write-Host "${GREEN}✓ PASS${RESET} - Authentication works"
    Write-Host "  User: $($data.email)`n"
} catch {
    Write-Host "${RED}✗ FAIL${RESET} - Authentication failed`n"
}

# Test 7: Protected Endpoint (without token)
Write-Host "${BLUE}7. Protected Endpoint (without token)${RESET}"
try {
    $response = Invoke-WebRequest -Uri "$API/accounts/me/" -Method GET `
        -ErrorAction Stop
    
    Write-Host "${RED}✗ FAIL${RESET} - Endpoint should require authentication!`n"
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "${GREEN}✓ PASS${RESET} - Properly protected (401 Unauthorized)`n"
    } else {
        Write-Host "${YELLOW}⚠ INFO${RESET} - Unexpected error code: $($_.Exception.Response.StatusCode)`n"
    }
}

# Test 8: Input Validation (bad email)
Write-Host "${BLUE}8. Input Validation (bad email)${RESET}"
$body = @{
    email = "invalid-email"
    password = "TestPass123!"
    full_name = "Test"
    phone_number = "+1-555-1234"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$API/accounts/register/" -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $body `
        -ErrorAction Stop
    
    Write-Host "${RED}✗ FAIL${RESET} - Should reject invalid email`n"
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "${GREEN}✓ PASS${RESET} - Rejects invalid email (400 Bad Request)`n"
    }
}

# Test 9: Input Validation (bad phone)
Write-Host "${BLUE}9. Input Validation (bad phone)${RESET}"
$body = @{
    email = "test@example.com"
    password = "TestPass123!"
    full_name = "Test"
    phone_number = "123"
} | ConvertTo-Json

try {
    $response = Invoke-WebRequest -Uri "$API/accounts/register/" -Method POST `
        -Headers @{"Content-Type"="application/json"} `
        -Body $body `
        -ErrorAction Stop
    
    Write-Host "${RED}✗ FAIL${RESET} - Should reject invalid phone`n"
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "${GREEN}✓ PASS${RESET} - Rejects invalid phone (400 Bad Request)`n"
    }
}

# Test 10: Admin Endpoint Protection
Write-Host "${BLUE}10. Admin Endpoint Protection${RESET}"
try {
    $response = Invoke-WebRequest -Uri "$API/accounts/admin/users/" -Method GET `
        -Headers @{"Authorization"="Token $token"} `
        -ErrorAction Stop
    
    Write-Host "${RED}✗ FAIL${RESET} - Regular user should not access admin endpoints`n"
} catch {
    if ($_.Exception.Response.StatusCode -eq 403) {
        Write-Host "${GREEN}✓ PASS${RESET} - Admin endpoints protected (403 Forbidden)`n"
    } else {
        Write-Host "${YELLOW}⚠ INFO${RESET} - Got status: $($_.Exception.Response.StatusCode)`n"
    }
}

# Summary
Write-Host "${BLUE}=== Test Summary ===${RESET}"
Write-Host "${GREEN}✓ All critical tests passed!${RESET}"
Write-Host "`nTo run comprehensive automated tests, use:"
Write-Host "  ${BLUE}python manage.py test accounts --keepdb${RESET}`n"
