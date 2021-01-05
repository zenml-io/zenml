var initTriggerNavBar=()=>{if($(window).width()<768){$("#navbar-toggler").trigger("click")}}
var scrollToActive=()=>{var navbar=document.getElementById('site-navigation')
var active_pages=navbar.querySelectorAll(".active")
var active_page=active_pages[active_pages.length-1]
if(active_page!==undefined&&active_page.offsetTop>($(window).height()*.5)){navbar.scrollTop=active_page.offsetTop-($(window).height()*.2)}}
var sbRunWhenDOMLoaded=cb=>{if(document.readyState!='loading'){cb()}else if(document.addEventListener){document.addEventListener('DOMContentLoaded',cb)}else{document.attachEvent('onreadystatechange',function(){if(document.readyState=='complete')cb()})}}
function toggleFullScreen(){var navToggler=$("#navbar-toggler");if(!document.fullscreenElement){document.documentElement.requestFullscreen();if(!navToggler.hasClass("collapsed")){navToggler.click();}}else{if(document.exitFullscreen){document.exitFullscreen();if(navToggler.hasClass("collapsed")){navToggler.click();}}}}
var initTooltips=()=>{$(document).ready(function(){$('[data-toggle="tooltip"]').tooltip();});}
var initTocHide=()=>{var scrollTimeout;var throttle=200;var tocHeight=$("#bd-toc-nav").outerHeight(true)+$(".bd-toc").outerHeight(true);var hideTocAfter=tocHeight+200;var checkTocScroll=function(){var margin_content=$(".margin, .tag_margin, .full-width, .full_width, .tag_full-width, .tag_full_width, .sidebar, .tag_sidebar, .popout, .tag_popout");margin_content.each((index,item)=>{var topOffset=$(item).offset().top-$(window).scrollTop();var bottomOffset=topOffset+$(item).outerHeight(true);var topOverlaps=((topOffset>=0)&&(topOffset<hideTocAfter));var bottomOverlaps=((bottomOffset>=0)&&(bottomOffset<hideTocAfter));var removeToc=(topOverlaps||bottomOverlaps);if(removeToc&&window.pageYOffset>20){$("div.bd-toc").removeClass("show")
return false}else{$("div.bd-toc").addClass("show")};})};$(window).on('scroll',function(){if(!scrollTimeout){scrollTimeout=setTimeout(function(){checkTocScroll();scrollTimeout=null;},throttle);}});}
var collapsibleListener=()=>{let expandUl=($ul)=>{if($ul.hasClass("collapse-ul")){$ul.removeClass("collapse-ul")
$ul.next("i").removeClass("fa-chevron-down").addClass("fa-chevron-up")}}
$elem=$("li.active")
for(el of $elem){$ul=$(el).closest("ul")
expandUl($ul)
$ulChild=$(el).children("ul")
expandUl($ulChild)
$p=$ul.prev()
if($p.is(".caption, .collapsible-parent")){$p.find("i").removeClass("fa-chevron-down").addClass("fa-chevron-up")}}
$(".collapsible-parent>i, .caption.collapsible-parent").on("click",function(e){e.stopPropagation()
$i=$(this)
$collapsibleParent=$i.closest(".collapsible-parent")
if($collapsibleParent.prop("tagName")=="P"){$ul=$collapsibleParent.next("ul")}else{$ul=$collapsibleParent.find("ul:first")}
$ul.toggle(0,function(){if(!$i.is(".fas")){$i=$i.find("i")}
if($i.hasClass("fa-chevron-up")){$i.removeClass("fa-chevron-up")
$i.addClass("fa-chevron-down")}else{$i.removeClass("fa-chevron-down")
$i.addClass("fa-chevron-up")}})})}
var initThebeSBT=()=>{var title=$("div.section h1")[0]
if(!$(title).next().hasClass("thebe-launch-button")){$("<button class='thebe-launch-button'></button>").insertAfter($(title))}
initThebe();}
sbRunWhenDOMLoaded(initTooltips)
sbRunWhenDOMLoaded(initTriggerNavBar)
sbRunWhenDOMLoaded(scrollToActive)
sbRunWhenDOMLoaded(initTocHide)
sbRunWhenDOMLoaded(collapsibleListener)
