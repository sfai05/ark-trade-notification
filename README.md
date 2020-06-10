# ark-trades-notification
Get telegram message of [ARK Intraday trades](https://ark-funds.com/trade-notifications) which run on GCP Cloudfunction

Build on [Serverless Framework](https://www.serverless.com/)



## Installation

### Setup

> create a new pubsub topic

```shell
$ gcloud pubsub topics create hourly-trigger
```

> setup schedule job for the pubsub topic

```shell
$ gcloud scheduler jobs create pubsub hourly-trigger --schedule "0 * * * *" --topic hourly-trigger --message-body "1"
```

> setup serverless config file ( serverless.yml )

```shell
$ cp serverless.yml.templete serverless.yml
```

- Update variable in `serverless.yml`

> deploy to GCP
```shell
$ npm install
$ sls deploy
```