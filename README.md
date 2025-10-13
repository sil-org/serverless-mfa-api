# ARCHIVED

This repository is archived. It has been superseded by [serverless-mfa-api-go](https://github.com/sil-org/serverless-mfa-api-go).

# Serverless MFA API
A Serverless API for registering and validating Multi-Factor Authentication methods.

Currently supports Time-based One Time Passwords (TOTP) and FIDO U2F devices (YubiKeys).

For details about the various API endpoints, see
[the RAML file](https://github.com/silinternational/serverless-mfa-api/blob/main/api.raml).

## Basic Workflow

- A consumer of this API does a `POST` to `/api-key`, providing an email
  address.
  * NOTE: To keep this API from being wide open to anyone, we protect our
    endpoints at/under `/api-key` with API Gateway's built-in api keys, which
    must be provided as an `x-api-key` header in the HTTP request.
- We create a new API Key and email it to that email address.
  * NOTE: At the moment, we do not actually send that email, since our use case
    is so limited that we can simply look up the API Key in the database. For
    local development, run `make list-dev-api-keys` to see it.
- The consumer does a `POST` to `/api-key/activate`, providing the email address
  and the API Key.
- We respond with an API Secret (which is actually an AES key, which we will use
  for encrypting their data), saving a strongly hashed copy of that API
  Secret for validating later calls that provide the API Secret.
  
### TOTP
- The consumer does a `POST` to `/totp`, providing their API Key and API Secret
  in the headers.
- We respond with a UUID, TOTP key, and QR Code, and we encrypt that TOTP key
  using the API Secret, storing the result.
- The consumer at some point does a `POST` to `/totp/{uuid}/validate`, providing
  their API Key and API Secret in the headers and the 6-digit code in the body.
- We get the TOTP records we have for that API Key, retrieve the one with the
  given UUID, use the (validated) API Secret to decrypt that TOTP key, and use
  the TOTP key to check the given 6-digit code for validity.
  
### U2F Registration
- The consumer does a `POST` to `/u2f`, providing their API Key and API Secret
  in the headers as well as the `appId` in the JSON body.
- We respond with an object including the UUID for further API calls as well as
  the challenge object to be passed along to the browser's `u2f.register()` call.
- The consumer uses the `u2f.register()` javascript API call in the browser.
- The end user inserts their FIDO U2F device and the light should be blinking and
  the user presses the button on the device.
- Pressing the button will trigger the callback method provided to the `u2f.register()`
  call which should pass the response object to the consumer's service, which in turn
  can make a `PUT` call to `/u2f/{uuid}` with a JSON body including a property named
  `signResult` with a value of the object returned from the U2F device.
- We will validate the response and store the `keyHandle` and `publicKey` encrypted by
  the consumer's API Secret and respond with a success or error message.

### U2F Authentication
- The consumer does a `POST` to `/u2f/{uuid}/auth`, providing their API Key and API Secret
  in the headers.
- We respond with the challenge object to be passed along to the browser's `u2f.sign()`
  call.
- The end user inserts their FIDO U2F device and the light should be blinking and
  the user presses the button on the device.
- Pressing the button will trigger the callback method provided to the `u2f.sign()`
  call which should pass the response object to the consumer's service, which in turn
  can make a `PUT` call to `/u2f/{uuid}/auth` with a JSON body including a property named
  `signResult` with a value of the object returned from the U2F device.
- We will validate the signResult and respond with a success or error message.

## Notes about FIDO U2F
- [FIDO U2F](https://www.yubico.com/solutions/fido-u2f/) is still relatively new with very limited support
  by browsers. In fact it is really only supported in Chrome without the need of installing extensions.
- Interaction with U2F devices either requires integration at a very low level or the use of
  a higher level javascript API. Oddly enough, the javascript API is not maintained in
  a distributable format. A copy of it can be obtained from YubiCo at https://demo.yubico.com/js/u2f-api.js
  or as part of a demo application from Google's GitHub: https://raw.githubusercontent.com/google/u2f-ref-code/master/u2f-gae-demo/war/js/u2f-api.js
- The `appId` used in the registration process must match the URL of the page where the user is authenticating and it
  must be HTTPS. It does  not need the full path though, so https://myapp.com is sufficient if the page is at
  https://myapp.com/auth/login.

## Automated Backups ##
While DynamoDB supports On Demand backups as well as Continuous Backups with
Point-in-time Recovery (PITR), both of these methods [restore to a new
table](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html)
rather than restoring to the existing DynamoDB table. While turning on
Point-in-time Recovery is certainly not a bad idea, we have ended up using an
alternate approach to make restores easier.

The **[shevchenkos/DynamoDbBackUp](https://github.com/shevchenkos/DynamoDbBackUp)**
software sets up Lambda functions that are triggered each time the associated
DynamoDB table is changed, and it backs up the records to an S3 bucket. We used
it to set up automated backups for each of the DynamoDB tables used by this
repo. We also forked it (to https://github.com/silinternational/DynamoDbBackUp)
in case the original "shevchenkos/DynamoDbBackUp" repo is ever deleted, but if
the original repo is available use it, as it will more likely be up-to-date.

For the shevchenkos/DynamoDbBackUp software to be able to make the necessary
changes in your AWS account, you will need to set up an IAM user with an Access
Key and Secret and with a policy similar to the following. Note that you will
need to replace `YOUR IP ADDRESS BLOCK CIDR` with a real value (for the IP
address or range of addresses from which you want the following commands to
allowed). You may also want to narrow down the breadth of permissions granted
here, further restrict statements by IP CIDR, restrict S3 paths, etc.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "iam:CreateRole",
            "Resource": "arn:aws:iam::*:role/*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "iam:*",
            "Resource": "arn:aws:iam::*:role/LambdaBackupDynamoDBToS3",
            "Condition": {
                "IpAddress": {
                    "aws:SourceIp": "YOUR IP ADDRESS BLOCK CIDR"
                }
            }
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:*"
            ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:*"
            ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:AttachRolePolicy",
                "iam:CreatePolicy",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:DeleteRolePolicy",
                "iam:GetRole",
                "iam:PassRole",
                "iam:PutRolePolicy"
            ],
            "Resource": [
                "arn:aws:iam:::*",
                "arn:aws:iam:::role/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "lambda:*"
            ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:*"
            ],
            "Resource": [
                "arn:aws:logs:*::log-group:*:log-stream:"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::*",
                "arn:aws:s3:::*/*"
            ]
        }
    ]
}
```

Once you have the shevchenkos/DynamoDbBackUp software set up on your computer,
you can use commands like the following to set up your automated backups.

**Create the S3 bucket:**
```
gulp deploy-s3-bucket \
    --s3bucket yourorg.backups.dynamodb.mfa-api \
    --s3region us-east-1
```
(Note: Some of these commands, including the one above, had to be run twice to
get past an apparent race condition.)

If actually setting up these backups for your use of this library, you will need
to run the following commands once for each of the production tables (currently `mfa-api_prod_api-key`, `mfa-api_prod_totp`, and `mfa-api_prod_u2f`)

**Set up the Lambda function for backing up changes:**
```
gulp deploy-lambda \
    --s3bucket yourorg.backups.dynamodb.mfa-api \
    --s3prefix mfa-api_prod_api-key \
    --s3region us-east-1 \
    --dbregion us-east-1 \
    --lName backup_dynamodb_mfa-api_prod_api-key \
    --lRegion us-east-1 \
    --lAlias active \
    --lRoleName LambdaBackupDynamoDBToS3 \
    --lTimeout 60
```

**Set up the event to trigger the Lambda function when a specific DynamoDB
table is changed:**
```
gulp deploy-lambda-event \
    --dbtable mfa-api_prod_api-key \
    --dbregion us-east-1 \
    --lName backup_dynamodb_mfa-api_prod_api-key \
    --lRegion us-east-1 \
    --lAlias active
```

**Do an initial full backup:**
```
gulp backup-full \
    --s3bucket yourorg.backups.dynamodb.mfa-api \
    --s3prefix mfa-api_prod_api-key \
    --s3region us-east-1 \
    --dbtable mfa-api_prod_api-key \
    --dbregion us-east-1
```

If you want to **do a restore** to a specific point in time (in this example,
Thu, 25 Jan 2018 22:10:00 GMT), you would run the following:
```
gulp restore \
    --s3bucket yourorg.backups.dynamodb.mfa-api \
    --s3prefix mfa-api_prod_totp \
    --s3region us-east-1 \
    --dbtable mfa-api_prod_totp \
    --dbregion us-east-1 \
    --restoretime 1516918200000
```
(Note: The restore time is a JavaScript timestamp, in milliseconds.)

## Running locally

To run this locally (such as for development)...

1. Open a terminal to **THIS** repo's root folder and run the following:
   - `make dynamodb-tables`
     * NOTE: You may need to run this twice. If it gives an error message,
       trying again should work. I think it's a timing issue, where it tries to
       create the dynamodb tables before the local dynamodb is _actually_ up
       enough to be ready for interaction.
   - `make dev-server`
2. Add and activate api-key entry for yourself in your local serverless-mfa-api:
   - Submit a `POST` to <https://localhost:8080/prod/api-key> with a JSON body
     like the following:
     ```json
     { "email": "local@example.com" }
     ```
     It should return a `204 No Content` response.
   - Run `make list-dev-api-keys`, and copy the "value" parameter's value.
   - Do a `POST` to <https://localhost:8080/prod/api-key/activate>, with a JSON
     body like the following:
     ```json
     {
     "email": "local@example.com",
     "apiKey": "the-value-parameter-from-the-dynamo-db-table"
     }
     ```
     It should return a `200 OK` with a JSON body containing an apiSecret that
     you will need. When copying that value, make sure you include any trailing
     equals signs (`=`).
3. Clone the <https://github.com/silinternational/idp-in-a-box> repo.
4. Put the apiSecret returned (including any trailing `=` signs) and the apiKey
   value you used in the JSON body into your local idp-in-a-box code's
   `/docker-compose/broker/local.env` file, both for the `MFA_TOTP_*` and
   `MFA_U2F_*` environment variables, something like this (but using **YOUR**
   values for the apiKey and apiSecret entries, not these dummy/sample values):
   ```
   MFA_TOTP_apiBaseUrl=http://localhost:8080/
   MFA_TOTP_apiKey=347a15dc60f014bdd93e4fc59aab607b022c8e19
   MFA_TOTP_apiSecret=za3c5Op8XgQcWNK16Rg6Th3ndmJ2ZTGL4uEldAJxDes=
   
   MFA_U2F_apiBaseUrl=http://localhost:8080/
   MFA_U2F_apiKey=347a15dc60f014bdd93e4fc59aab607b022c8e19
   MFA_U2F_apiSecret=za3c5Op8XgQcWNK16Rg6Th3ndmJ2ZTGL4uEldAJxDes= 
   ```
5. Bring up the `idp-in-a-box` repo. See that repo's README.md for instructions.

## Serverless

To start a local container for development of Serverless configuration:

```
docker compose run --rm dev bash
```

## Credential Rotation

### AWS Serverless User

1. Use the Terraform CLI to taint the old access key
```
terraform taint module.serverless-user.aws_iam_access_key.serverless
```
2. Run a new plan on Terraform Cloud
3. Review the new plan and apply if it is correct
4. Copy the new key and secret from the Terraform output into GitHub Repository Secrets

## Glossary

- `API Key`: A hex string used to identify calls to most of the endpoints on
  this API. We store a copy of this in the database.
- `API Secret`: A base-64 encoded random value used to encrypt/decrypt the
  consumer's data. We store a salted, stretched hash of this (as we
  would a password) for validating later calls that provide an API Secret.
- `TOTP Key`: The secret used for generating TOTP values. This is provided to
  the consumer of this API for them to show as a string / QR Code to their end
  user. We store an encrypted copy of this (encrypted using the API Secret) so
  that when we need to verify given 6-digit code, we can do so.
