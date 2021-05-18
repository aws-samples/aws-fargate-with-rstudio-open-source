######################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# OFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
######################################################################################

#verify Athena credentials by inspecting results from command below
Sys.getenv()

library(rJava)
library(RJDBC)

URL <- 'https://s3.amazonaws.com/athena-downloads/drivers/JDBC/SimbaAthenaJDBC-2.0.16.1000/AthenaJDBC42.jar'
fil <- basename(URL)

#download the file into current working directory

if (!file.exists(fil)) download.file(URL, fil)
#verify that the file has been downloaded successfully
fil
list.files()

#set up driver connection to JDBC
drv <- JDBC(driverClass="com.simba.athena.jdbc.Driver", "AthenaJDBC42.jar", identifier.quote="'")

con <- jdbcConnection <- dbConnect(drv, Sys.getenv("JDBC_URL"), S3OutputLocation=Sys.getenv("S3_BUCKET"), Workgroup=Sys.getenv("ATHENA_WG"), User=Sys.getenv("ATHENA_USER"), Password=Sys.getenv("ATHENA_PASSWORD"))

dbListTables(con)

# run a sample query
dfelb=dbGetQuery(con, "SELECT * FROM sampledb.elb_logs limit 10")
head(dfelb,2)
