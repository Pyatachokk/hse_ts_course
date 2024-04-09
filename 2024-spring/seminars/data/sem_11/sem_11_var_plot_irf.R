plotIRF <-
  function (x, vnames = NULL, snames = NULL, vlabels = NULL, slabels = NULL,
            main = NULL, sub = NULL, lty = NULL, lwd = NULL, col = NULL, ylim = NULL,
            ylab = NULL, xlab = NULL, nc, mar.multi = c(0, 4, 0, 4),
            oma.multi = c(6, 4, 6, 4), adj.mtext = NA, padj.mtext = NA, col.mtext = NA, ...)
  {
    # op <- par(no.readonly = TRUE)
    # on.exit(par(op))
    ##
    ## Check arguments
    ##
    inames <- x$impulse
    if (is.null(snames)) {
      snames <- inames
    }
    else {
      snames <- as.character(snames)
      if (!(all(snames %in% inames))) { stop("\nInvalid shock name(s) supplied.\n") }
      else { inames <- snames }
    }
    nvi <- length(inames)
    rnames <- x$response
    if (is.null(vnames)) {
      vnames <- rnames
    }
    else {
      vnames <- as.character(vnames)
      if (!(all(vnames %in% rnames))) { stop("\nInvalid variable name(s) supplied.\n") }
      else { rnames <- vnames }
    }
    nvr <- length(rnames)
    if (is.null(slabels)) {
      slabels <- snames
    }
    else {
      if (!(length(slabels) == length(snames))) { 
        stop("\nNUmber of labels for shocks in slabels does not math number of shocks in snames.\n") }
    }
    if (is.null(vlabels)) {
      vlabels <- vnames
    }
    else {
      if (!(length(slabels) == length(snames))) { 
        stop("\nNUmber of labels for shocks in slabels does not math number of shocks in snames.\n") }
    }
    
    ##
    ## Presetting certain plot-argument
    ##
    ifelse(is.null(lty), lty <- c(1, 1, 2, 2), lty <- rep(lty, 4)[1:4])
    ifelse(is.null(lwd), lwd <- c(1, 1, 1, 1), lwd <- rep(lwd, 4)[1:4])
    ifelse(is.null(col), col <- c("black", "gray", "red", "red"), col <- rep(col, 4)[1:4])
    
    ##
    ## Extract data for variable rname from varirf object
    ##
    dataplot.r <- function(x, rname){
      impulses <- NULL
      for(j in 1:length(x$irf)){
        impulses <- cbind(impulses, x$irf[[j]][,rname])
        colnames(impulses)[j] <- names(x$irf)[j]
      }
      range <- range(impulses)
      upper <- NULL
      lower <- NULL
      if(x$boot){
        for(j in 1:length(x$irf)){
          upper <- cbind(upper, x$Upper[[j]][,rname])
          lower <- cbind(lower, x$Lower[[j]][,rname])
          colnames(upper)[j] <- names(x$irf)[j]
          colnames(lower)[j] <- names(x$irf)[j]
        }
        range <- range(cbind(impulses, upper, lower))
      }
      if ((x$model == "varest") || (x$model == "vec2var")) {
        text1 <- "Impulse Response"
      } else if (x$model == "svarest") {
        text1 <- "SVAR Impulse Response"
      } else if (x$model == "svecest") {
        text1 <- "SVECM Impulse Response"
      }
      if (x$cumulative)  text1 <- paste("Cumulative", text1, sep = " ")
      text2 <- ""
      if (x$boot) text2 <- paste((1 - x$ci) * 100, "% Bootstrap CI, ", x$runs, "runs")
      
      result <- list(impulses = impulses, upper = upper, 
                     lower = lower, range = range, 
                     text1 = text1, text2 = text2)
      return(result)
    }
    ##
    ## Plot function for irf per impulse and response
    ##
    plot.single <- function(x, iname, rname, ylabel, slabel,...) {
      x$text1 <- paste(x$text1, "from", slabel, sep = " ")
      ifelse(is.null(main), main <- x$text1, main <- main)
      ifelse(is.null(sub), sub <- x$text2, sub <- sub)
      xy <- xy.coords(x$impulses[, iname])
      ifelse(is.null(xlab), xlabel <- "", xlabel <- xlab)
      ifelse(is.null(ylim), ylim <- x$range, ylim <- ylim)
      plot(xy, type = "l", ylim = ylim, 
           col = col[1], lty = lty[1], 
           lwd = lwd[1], axes = FALSE, 
           ylab = paste(ylabel), xlab = paste(xlab), ...)
      title(main = main, sub = sub, ...)
      axis(1, at = xy$x, labels = c(0:(length(xy$x) - 1)))
      axis(2, ...)
      box()
      if (!is.null(x$upper)) lines(x$upper[, iname], col = col[3], lty = lty[3], lwd = lwd[3])
      if (!is.null(x$lower)) lines(x$lower[, iname], col = col[3], lty = lty[3], lwd = lwd[3])
      abline(h = 0, col = col[2], lty = lty[2], lwd = lwd[2])
    }
    ##
    ## Plot IRFs
    ##
    for(i in 1:nvr){
      dp.r <- dataplot.r(x, rname = rnames[i])
      for(j in 1:nvi){
        plot.single(dp.r, iname = inames[j], rname = rnames[i], 
                    ylabel = vlabels[i], slabel = slabels[j], ...)
        # if (nvr > 1) par(ask = TRUE)
      }
    }
  }