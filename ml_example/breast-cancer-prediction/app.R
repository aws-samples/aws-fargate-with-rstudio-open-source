library(shiny)

test_data <- readRDS('./breast_cancer_test_data.rds')
gbmFit <- readRDS('./gbm_model.rds')
preProcessor <- readRDS('./preProcessor.rds')

# Define UI for miles per gallon app ----
ui <- fluidPage(
    
    # App title ----
    titlePanel("Breast Cancer"),
    
    # Sidebar layout with input and output definitions ----
    sidebarLayout(
        
        # Sidebar panel for inputs ----
        sidebarPanel(
            
            # Input: Selector for variable to plot against mpg ----
            selectInput("variable", "Variable:",
                        c("Class" = "Class",
                          "Transmission" = "am",
                          "Gears" = "gear")),
            
            # Input: Checkbox for whether outliers should be included ----
            checkboxInput("outliers", "Show outliers", TRUE)
            
        ),
        
        # Main panel for displaying outputs ----
        mainPanel(
            
            # Output: Formatted text for caption ----
            h3(textOutput("caption")),
            
            # Output: Verbatim text for data summary ----
            verbatimTextOutput("summary"),
            
            # Output: Plot of the data ----
            plotOutput("scatterPlot", click = "plot_click"),
            
            # Output: present click info
            verbatimTextOutput("info")
            
        )
    )
)

# Define server logic to plot various variables against mpg ----
server <- function(input, output) {

    # Generate a summary of the dataset ----
    # The output$summary depends on the datasetInput reactive
    # expression, so will be re-executed whenever datasetInput is
    # invalidated, i.e. whenever the input$dataset changes
    output$summary <- renderPrint({
        #dataset <- test_data
        summary(test_data)
    })
    
    # Generate a plot of the requested variable against mpg ----
    # and only exclude outliers if requested
    output$scatterPlot <- renderPlot({
        splom(test_data[,2:10])
    })
    
    output$info <- renderText({
        paste0("x=", input$plot_click$x, "\ny=", input$plot_click$y)
    })
    
}

# Create Shiny app ----
shinyApp(ui, server)