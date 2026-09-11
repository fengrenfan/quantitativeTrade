# 构建阶段
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /src

# Maven 中央仓镜像可覆盖（国内服务器建议用镜像源）
ARG MAVEN_MIRROR=https://repo.maven.apache.org/maven2
RUN mkdir -p /root/.m2 \
 && printf '%s\n' \
      '<?xml version="1.0" encoding="UTF-8"?>' \
      '<settings>' \
      '  <mirrors>' \
      '    <mirror>' \
      '      <id>central-mirror</id>' \
      '      <mirrorOf>central</mirrorOf>' \
      '      <name>central-mirror</name>' \
      "      <url>${MAVEN_MIRROR}</url>" \
      '    </mirror>' \
      '  </mirrors>' \
      '</settings>' > /root/.m2/settings.xml

COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B clean package -DskipTests

# 运行阶段
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /src/target/*.jar app.jar
EXPOSE 8081
ENTRYPOINT ["java", "-jar", "app.jar"]
