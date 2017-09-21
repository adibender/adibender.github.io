library(shiny)


ui <- fluidPage(
  selectInput("plotType_picker", "Pick plot type",
              choices = c("boxplot","histogram")),
  plotOutput("my_plot")
)
server <- function(input, output) {
  x <- rnorm(100)
  output$my_plot <- renderPlot({
    if (input$plotType_picker == "boxplot") {
      boxplot(x, col = "slategray3")
    } else
      hist(x, col = "slategray3")
  })
}


shinyApp(ui = ui, server = server)