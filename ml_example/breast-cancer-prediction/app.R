library(shiny)
library(ggplot2)

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
            
            # Input: Selector for variable to plot on x axis ----
            selectInput("variable_x", "Variable on X:",
                        c("Cell Size" = "Cell.size",
                          "Cell Shape" = "Cell.shape",
                          "Marg adhesion" = "Marg.adhesion")),
            
            # Input: Selector for variable to plot on y axis ----
            selectInput("variable_y", "Variable on Y:",
                        c("Cell Shape" = "Cell.shape",
                          "Cell Size" = "Cell.size",
                          "Marg adhesion" = "Marg.adhesion")),
            
            # Input: Checkbox for whether outliers should be included ----
            #checkboxInput("outliers", "Show outliers", TRUE)
            
        ),
        
        # Main panel for displaying outputs ----
        mainPanel(
            
            # Output: Formatted text for caption ----
            h3(textOutput("caption")),
            
            # Output: Verbatim text for data summary ----
            verbatimTextOutput("summary"),
            
            # Output: Plot of the data ----
            # was  click = "plot_click"
            plotOutput("scatterPlot", brush = "plot_brush"),
            
            # Output: present click info
            #verbatimTextOutput("info")
            tableOutput("info")
            
        )
    )
)

# Define server logic to plot various variables against mpg ----
server <- function(input, output) {
    
    # Compute the formula text ----
    # This is in a reactive expression since it is shared by the
    # output$caption and output$mpgPlot functions
    formulaText <- reactive({
        paste(input$variable_y, "~", input$variable_x)
    })

    # Return the formula text for printing as a caption ----
    output$caption <- renderText({
        formulaText()
    })
    
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
        #splom(test_data[,2:10])
        plot(as.formula(formulaText()), data = test_data)
        #ggplot(test_data, aes(x=input$variable_x, y=input$variable_y)) + geom_point()
    })
    
    output$info <- renderTable({
        # With base graphics, need to tell it what the x and y variables are.
        #nearPoints(test_data, input$plot_click, 
        #           xvar = "Cl.thickness", yvar = "Epith.c.size")
        # nearPoints() also works with hover and dblclick events
        brushedPoints(test_data, input$plot_brush, 
                      xvar = input$variable_x, yvar = input$variable_y)
    })
    
}

# Create Shiny app ----
shinyApp(ui, server)