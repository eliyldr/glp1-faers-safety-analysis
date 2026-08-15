library(arrow)
library(dplyr)
library(ggplot2)

data <- read_parquet("final_case_analysis.parquet")
head(data)

# Q3: Is the proportion of patients experiencing nausea significantly different from 20% among Ozempic users?

ozempic_data <- data %>% filter(drugname == "OZEMPIC")
n_ozempic <- nrow(ozempic_data) #Total number of Ozempic users (n)

x_nausea <- sum(ozempic_data$nausea_binary == 1, na.rm = TRUE)

p0 <- 0.20 #20%
expected_success <- n_ozempic * p0
expected_failure <- n_ozempic * (1 - p0)
cat("Expected number of Nausea cases (n*p0):", expected_success)
cat("Expected number of Non-nausea cases (n*(1-p0)):", expected_failure)

prop.test(x = x_nausea, n = n_ozempic, p = p0, alternative = "two.sided")

# Q4: Is there a significant difference in the proportion of patients experiencing nausea between Ozempic and Trulicity users?

filtered_data <- data %>% 
  filter(drugname %in% c("OZEMPIC", "TRULICITY"))

summary_stats <- filtered_data %>%
  group_by(drugname) %>%
  summarise(
    n_total = n(),
    x_event = sum(nausea_binary == 1, na.rm = TRUE),
    .groups = "drop"
  )

print(summary_stats)

summary_stats <- summary_stats %>%
  mutate(failures = n_total - x_event)

cat("Success/Failure counts for assumption check: ")
print(summary_stats[, c("drugname", "x_event", "failures")])

prop.test(x = summary_stats$x_event, n = summary_stats$n_total, alternative = "two.sided")


nausea_labels <- ifelse(filtered_data$nausea_binary == 1, "Nausea", "No Nausea")
mosaic_table <- table(filtered_data$drugname, nausea_labels)

mosaicplot(mosaic_table, 
           main = "Mosaic Plot of Nausea Incidence by Drug", 
           xlab = "Drug Name", 
           ylab = "Nausea Status", 
           color = c("red", "lightblue"), # Red (Nausea) Blue (No Nausea)
           border = "black")

