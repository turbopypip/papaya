FROM golang:1.24-alpine AS builder

WORKDIR /usr/local/src

# dependencies
COPY ["app/go.mod", "app/go.sum", "./"]

RUN go mod download

# build
COPY app ./
RUN go build -o ./bin/app cmd/app/main.go

FROM alpine AS runner

COPY --from=builder /usr/local/src/bin/app /

CMD ["./app"]
